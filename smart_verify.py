#!/usr/bin/env python3
"""
Smart Data Verifier for JuanStudio
===================================
Comprehensive verification with auto-fix capabilities.

Usage:
  python smart_verify.py --check-only      # Check without fixing
  python smart_verify.py --auto-fix        # Auto-fix all issues
  python smart_verify.py --pre-deploy      # Strict mode for deployment
"""

import sqlite3
import json
import sys
import subprocess
import re
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter

# Configuration
DATABASE_PATH = "data/juanstudio_analytics.db"
JSON_PATH = "frontend/public/data/analytics-v2.json"
EXPECTED_PAGES = 14

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def ok(msg):
    return f"{Colors.GREEN}OK{Colors.END} ({msg})"

def warn(msg):
    return f"{Colors.YELLOW}WARN{Colors.END} ({msg})"

def error(msg):
    return f"{Colors.RED}ERROR{Colors.END} ({msg})"

def fixed(msg):
    return f"{Colors.BLUE}FIXED{Colors.END} ({msg})"


class DataVerifier:
    def __init__(self, db_path=DATABASE_PATH, json_path=JSON_PATH):
        self.db_path = db_path
        self.json_path = json_path
        self.results = {
            'passed': 0,
            'warnings': 0,
            'errors': 0,
            'fixed': 0
        }
        self.issues = []
        self.warnings_list = []

    def connect_db(self):
        return sqlite3.connect(self.db_path, timeout=30)

    # =========================================================================
    # CHECK 1: DUPLICATES
    # =========================================================================
    def check_duplicates(self, auto_fix=False):
        """Check for duplicate pages and posts."""
        print(f"\n[CHECK] Duplicates...", end=" ")

        conn = self.connect_db()
        cur = conn.cursor()

        # Check duplicate pages
        cur.execute("SELECT page_id, COUNT(*) as cnt FROM pages GROUP BY page_id HAVING cnt > 1")
        dup_pages = cur.fetchall()

        # Check duplicate posts
        cur.execute("SELECT post_id, COUNT(*) as cnt FROM posts GROUP BY post_id HAVING cnt > 1")
        dup_posts = cur.fetchall()

        if dup_pages or dup_posts:
            if auto_fix:
                fixed_count = self._fix_duplicates(conn, dup_pages, dup_posts)
                print(fixed(f"merged {fixed_count} duplicates"))
                self.results['fixed'] += 1
            else:
                msg = []
                if dup_pages:
                    msg.append(f"{len(dup_pages)} duplicate pages")
                if dup_posts:
                    msg.append(f"{len(dup_posts)} duplicate posts")
                print(error(", ".join(msg)))
                self.issues.append(f"Duplicates found: {', '.join(msg)}")
                self.results['errors'] += 1
        else:
            cur.execute("SELECT COUNT(*) FROM pages")
            page_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM posts")
            post_count = cur.fetchone()[0]
            print(ok(f"{page_count} pages, {post_count} posts"))
            self.results['passed'] += 1

        conn.close()

    def _fix_duplicates(self, conn, dup_pages, dup_posts):
        """Auto-fix duplicate entries by merging."""
        cur = conn.cursor()
        fixed_count = 0

        # Fix duplicate pages - keep the one with more posts
        for page_id, _ in dup_pages:
            # Get all instances of this page
            cur.execute("""
                SELECT p.rowid, p.page_id, COUNT(posts.post_id) as post_count
                FROM pages p
                LEFT JOIN posts ON posts.page_id = p.page_id
                WHERE p.page_id = ?
                GROUP BY p.rowid
                ORDER BY post_count DESC
            """, (page_id,))
            instances = cur.fetchall()

            # Keep first (most posts), delete rest
            keep_rowid = instances[0][0]
            for rowid, _, _ in instances[1:]:
                cur.execute("DELETE FROM pages WHERE rowid = ?", (rowid,))
                fixed_count += 1

        # Fix duplicate posts - keep most recent
        for post_id, _ in dup_posts:
            cur.execute("""
                SELECT rowid, publish_time FROM posts
                WHERE post_id = ?
                ORDER BY publish_time DESC
            """, (post_id,))
            instances = cur.fetchall()

            # Keep first (most recent), delete rest
            for rowid, _ in instances[1:]:
                cur.execute("DELETE FROM posts WHERE rowid = ?", (rowid,))
                fixed_count += 1

        conn.commit()
        return fixed_count

    # =========================================================================
    # CHECK 2: DATE VALIDATION
    # =========================================================================
    def check_dates(self, auto_fix=False):
        """Check for mixed date formats and invalid dates."""
        print(f"[CHECK] Date formats...", end=" ")

        conn = self.connect_db()
        cur = conn.cursor()

        cur.execute("SELECT post_id, publish_time FROM posts WHERE publish_time IS NOT NULL")
        posts = cur.fetchall()

        bad_format = []
        future_dates = []
        today = datetime.now()

        for post_id, pub_time in posts:
            if not pub_time:
                continue

            # Check for non-ISO format (contains '/' instead of '-')
            if '/' in str(pub_time):
                bad_format.append((post_id, pub_time))

            # Check for future dates
            try:
                if 'T' in str(pub_time):
                    date_str = pub_time.split('T')[0]
                else:
                    date_str = pub_time[:10]

                # Try to parse the date
                if '-' in date_str:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                elif '/' in date_str:
                    dt = datetime.strptime(date_str, '%m/%d/%Y')
                else:
                    continue

                if dt > today + timedelta(days=1):
                    future_dates.append((post_id, pub_time))
            except:
                pass

        if bad_format:
            if auto_fix:
                fixed_count = self._fix_dates(conn, bad_format)
                print(fixed(f"{fixed_count} dates normalized"))
                self.results['fixed'] += 1
            else:
                print(error(f"{len(bad_format)} dates in wrong format"))
                self.issues.append(f"{len(bad_format)} dates need normalization (MM/DD/YYYY -> ISO)")
                self.results['errors'] += 1
        elif future_dates:
            print(warn(f"{len(future_dates)} future dates detected"))
            self.warnings_list.append(f"{len(future_dates)} posts have future dates")
            self.results['warnings'] += 1
        else:
            # Get date range
            cur.execute("SELECT MIN(publish_time), MAX(publish_time) FROM posts")
            min_date, max_date = cur.fetchone()
            if min_date and max_date:
                print(ok(f"{min_date[:10]} to {max_date[:10]}"))
            else:
                print(ok("all dates valid"))
            self.results['passed'] += 1

        conn.close()

    def _fix_dates(self, conn, bad_dates):
        """Normalize dates to ISO format."""
        cur = conn.cursor()
        fixed_count = 0

        for post_id, pub_time in bad_dates:
            try:
                # Parse MM/DD/YYYY format
                if '/' in pub_time:
                    parts = pub_time.split('/')
                    if len(parts) == 3:
                        month, day, year = parts
                        # Handle year with time attached
                        if ' ' in year:
                            year = year.split(' ')[0]
                        iso_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}T00:00:00+0000"

                        cur.execute(
                            "UPDATE posts SET publish_time = ? WHERE post_id = ?",
                            (iso_date, post_id)
                        )
                        fixed_count += 1
            except Exception as e:
                print(f"\n  Warning: Could not fix date for {post_id}: {e}")

        conn.commit()
        return fixed_count

    # =========================================================================
    # CHECK 3: DATA COMPLETENESS
    # =========================================================================
    def check_completeness(self, auto_fix=False):
        """Check for missing required data."""
        print(f"[CHECK] Data completeness...", end=" ")

        conn = self.connect_db()
        cur = conn.cursor()

        issues = []

        # Check page count
        cur.execute("SELECT COUNT(*) FROM pages")
        page_count = cur.fetchone()[0]
        if page_count < EXPECTED_PAGES:
            issues.append(f"only {page_count}/{EXPECTED_PAGES} pages")

        # Check for pages with 0 followers
        cur.execute("SELECT page_name FROM pages WHERE followers_count = 0 OR followers_count IS NULL")
        no_followers = cur.fetchall()
        if no_followers:
            names = [n[0].replace('Juana Babe ', '') for n in no_followers[:3]]
            self.warnings_list.append(f"{len(no_followers)} pages missing followers: {', '.join(names)}...")

        # Check for posts with 0 views AND 0 reach (might be missing data)
        cur.execute("""
            SELECT COUNT(*) FROM posts
            WHERE (views_count = 0 OR views_count IS NULL)
            AND (reach_count = 0 OR reach_count IS NULL)
            AND post_type IN ('Videos', 'Reels', 'Live')
        """)
        no_views = cur.fetchone()[0]
        if no_views > 0:
            self.warnings_list.append(f"{no_views} video posts missing views/reach data")

        # Check for pages with 0 posts
        cur.execute("""
            SELECT p.page_name FROM pages p
            LEFT JOIN posts po ON p.page_id = po.page_id
            GROUP BY p.page_id
            HAVING COUNT(po.post_id) = 0
        """)
        empty_pages = cur.fetchall()
        if empty_pages:
            issues.append(f"{len(empty_pages)} pages have no posts")

        conn.close()

        if issues:
            print(error("; ".join(issues)))
            self.issues.extend(issues)
            self.results['errors'] += 1
        elif self.warnings_list:
            print(warn(f"{len(self.warnings_list)} minor issues"))
            self.results['warnings'] += 1
        else:
            print(ok("all data present"))
            self.results['passed'] += 1

    # =========================================================================
    # CHECK 4: SELF-COMMENTS
    # =========================================================================
    def check_self_comments(self, auto_fix=False):
        """Check if page self-comments are being tracked."""
        print(f"[CHECK] Self-comments...", end=" ")

        conn = self.connect_db()
        cur = conn.cursor()

        # Posts with comments but NULL page_comments (truly unfetched)
        # Note: page_comments = 0 is valid (means fetched but no self-comments)
        cur.execute("""
            SELECT COUNT(*) FROM posts
            WHERE comments_count > 0
            AND page_comments IS NULL
        """)
        missing_count = cur.fetchone()[0]

        # Also check total page_comments
        cur.execute("SELECT SUM(page_comments) FROM posts")
        total_page_comments = cur.fetchone()[0] or 0

        conn.close()

        if total_page_comments == 0 and missing_count > 0:
            if auto_fix:
                print(f"\n  Running fetch_comments.py...", end=" ")
                result = self._run_fetch_comments()
                if result:
                    print(fixed("comments fetched"))
                    self.results['fixed'] += 1
                else:
                    print(error("fetch failed"))
                    self.issues.append("Could not fetch comments - run manually")
                    self.results['errors'] += 1
            else:
                print(error("all page_comments are 0"))
                self.issues.append("Self-comments not fetched - run fetch_comments.py")
                self.results['errors'] += 1
        elif missing_count > 10:
            print(warn(f"{missing_count} posts may need comment fetch"))
            self.warnings_list.append(f"{missing_count} posts might have unfetched comments")
            self.results['warnings'] += 1
        else:
            print(ok(f"{total_page_comments} total page comments"))
            self.results['passed'] += 1

    def _run_fetch_comments(self):
        """Run the fetch_comments.py script."""
        script_path = Path(__file__).parent / "fetch_comments.py"
        if not script_path.exists():
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                timeout=300  # 5 minute timeout
            )
            return result.returncode == 0
        except Exception as e:
            print(f"\n  Error running fetch_comments: {e}")
            return False

    # =========================================================================
    # CHECK 5: DB vs JSON CONSISTENCY
    # =========================================================================
    def check_json_sync(self, auto_fix=False):
        """Check if JSON export matches database."""
        print(f"[CHECK] DB vs JSON sync...", end=" ")

        # Get DB counts
        conn = self.connect_db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM pages")
        db_pages = cur.fetchone()[0]

        # JSON only includes posts with engagement, so match that filter
        cur.execute("""
            SELECT COUNT(*) FROM posts
            WHERE reactions_total > 0 OR comments_count > 0 OR shares_count > 0
        """)
        db_posts = cur.fetchone()[0]

        cur.execute("SELECT MIN(publish_time), MAX(publish_time) FROM posts")
        db_min_date, db_max_date = cur.fetchone()

        conn.close()

        # Get JSON counts
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            json_pages = len(data.get('pages', []))
            json_posts = len(data.get('posts', []))

            # Check if counts match
            issues = []
            if db_pages != json_pages:
                issues.append(f"pages: DB={db_pages}, JSON={json_pages}")
            if db_posts != json_posts:
                issues.append(f"posts: DB={db_posts}, JSON={json_posts}")

            if issues:
                if auto_fix:
                    print(f"\n  Running export_static_data.py...", end=" ")
                    result = self._run_export()
                    if result:
                        print(fixed("JSON re-exported"))
                        self.results['fixed'] += 1
                    else:
                        print(error("export failed"))
                        self.issues.append("Could not re-export JSON")
                        self.results['errors'] += 1
                else:
                    print(error("; ".join(issues)))
                    self.issues.append(f"DB/JSON mismatch: {'; '.join(issues)}")
                    self.results['errors'] += 1
            else:
                print(ok(f"{json_pages} pages, {json_posts} posts match"))
                self.results['passed'] += 1

        except FileNotFoundError:
            if auto_fix:
                print(f"\n  Creating JSON export...", end=" ")
                result = self._run_export()
                if result:
                    print(fixed("JSON created"))
                    self.results['fixed'] += 1
                else:
                    print(error("export failed"))
                    self.results['errors'] += 1
            else:
                print(error("JSON file not found"))
                self.issues.append("JSON export missing - run export_static_data.py")
                self.results['errors'] += 1
        except json.JSONDecodeError:
            print(error("JSON file corrupted"))
            self.issues.append("JSON file is corrupted")
            self.results['errors'] += 1

    def _run_export(self):
        """Run the export_static_data.py script."""
        script_path = Path(__file__).parent / "export_static_data.py"
        if not script_path.exists():
            return False

        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                timeout=60
            )
            return result.returncode == 0
        except Exception as e:
            print(f"\n  Error running export: {e}")
            return False

    # =========================================================================
    # CHECK 6: DATA INTEGRITY
    # =========================================================================
    def check_integrity(self, auto_fix=False):
        """Check data integrity rules."""
        print(f"[CHECK] Data integrity...", end=" ")

        conn = self.connect_db()
        cur = conn.cursor()

        issues = []

        # Check for negative values
        cur.execute("""
            SELECT COUNT(*) FROM posts
            WHERE reactions_total < 0
            OR comments_count < 0
            OR shares_count < 0
            OR views_count < 0
        """)
        negative = cur.fetchone()[0]
        if negative > 0:
            issues.append(f"{negative} posts with negative values")

        # Check valid post types (including variations from different data sources)
        valid_types = {'Photos', 'Videos', 'Reels', 'Live', 'Text', 'Link', 'Links', 'Status', 'Event', 'Events', 'IMAGE', 'VIDEO', None, ''}
        cur.execute("SELECT DISTINCT post_type FROM posts")
        types = [r[0] for r in cur.fetchall()]
        invalid_types = [t for t in types if t not in valid_types]
        if invalid_types:
            issues.append(f"invalid post types: {invalid_types}")

        # Check engagement calculation (should be reactions + comments + shares)
        cur.execute("""
            SELECT COUNT(*) FROM posts
            WHERE total_engagement != (reactions_total + comments_count + shares_count)
            AND total_engagement IS NOT NULL
            AND reactions_total IS NOT NULL
        """)
        bad_engagement = cur.fetchone()[0]
        if bad_engagement > 0:
            self.warnings_list.append(f"{bad_engagement} posts have mismatched engagement calc")

        conn.close()

        if issues:
            print(error("; ".join(issues)))
            self.issues.extend(issues)
            self.results['errors'] += 1
        else:
            print(ok("all integrity checks passed"))
            self.results['passed'] += 1

    # =========================================================================
    # MAIN RUN
    # =========================================================================
    def run(self, mode='check-only'):
        """Run all verification checks."""
        auto_fix = mode in ('auto-fix', 'pre-deploy')

        print("=" * 60)
        print(f"{Colors.BOLD}JUANSTUDIO DATA VERIFICATION{Colors.END}")
        print("=" * 60)
        print(f"Mode: {mode}")
        print(f"Database: {self.db_path}")
        print(f"JSON: {self.json_path}")

        # Run all checks
        self.check_duplicates(auto_fix)
        self.check_dates(auto_fix)
        self.check_completeness(auto_fix)
        self.check_self_comments(auto_fix)
        self.check_json_sync(auto_fix)
        self.check_integrity(auto_fix)

        # Print summary
        print("\n" + "=" * 60)
        print(f"{Colors.BOLD}SUMMARY{Colors.END}")
        print("=" * 60)
        print(f"  Checks passed:  {self.results['passed']}")
        print(f"  Auto-fixed:     {self.results['fixed']}")
        print(f"  Warnings:       {self.results['warnings']}")
        print(f"  Errors:         {self.results['errors']}")

        if self.warnings_list:
            print(f"\n{Colors.YELLOW}WARNINGS:{Colors.END}")
            for w in self.warnings_list:
                print(f"  - {w}")

        if self.issues:
            print(f"\n{Colors.RED}ISSUES:{Colors.END}")
            for i in self.issues:
                print(f"  - {i}")

        print()

        # Determine exit code
        if mode == 'pre-deploy':
            # Pre-deploy mode: fail on any error OR warning
            if self.results['errors'] > 0:
                print(f"{Colors.RED}VERIFICATION FAILED - Do not deploy!{Colors.END}")
                return 1
            elif self.results['warnings'] > 0:
                print(f"{Colors.YELLOW}VERIFICATION PASSED WITH WARNINGS{Colors.END}")
                print("Review warnings before deploying.")
                return 0
            else:
                print(f"{Colors.GREEN}VERIFICATION PASSED - Safe to deploy!{Colors.END}")
                return 0
        else:
            # Normal mode: fail only on errors
            if self.results['errors'] > 0:
                print(f"{Colors.RED}VERIFICATION FAILED{Colors.END}")
                print("Run with --auto-fix to attempt automatic fixes.")
                return 1
            else:
                print(f"{Colors.GREEN}VERIFICATION PASSED{Colors.END}")
                return 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description='JuanStudio Data Verifier')
    parser.add_argument('--check-only', action='store_true', help='Check without fixing')
    parser.add_argument('--auto-fix', action='store_true', help='Auto-fix all issues')
    parser.add_argument('--pre-deploy', dest='pre_deploy', action='store_true', help='Strict mode for deployment')

    args = parser.parse_args()

    if args.auto_fix:
        mode = 'auto-fix'
    elif args.pre_deploy:
        mode = 'pre-deploy'
    else:
        mode = 'check-only'

    verifier = DataVerifier()
    return verifier.run(mode)


if __name__ == "__main__":
    sys.exit(main())
