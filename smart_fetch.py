#!/usr/bin/env python3
"""
Smart Facebook Data Fetcher with Rate Limiting and Resume Capability.

Features:
- Adaptive rate limiting with exponential backoff
- Progress tracking with resume capability
- Parallel page fetching (3 concurrent max)
- Sequential post processing within each page
- Checkpoint saving after each batch
"""

import json
import time
import argparse
import sqlite3
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from pathlib import Path
import requests

# Configuration
API_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
DATABASE_PATH = Path(__file__).parent / "data" / "juanstudio_analytics.db"
PROGRESS_FILE = Path(__file__).parent / "fetch_progress.json"
PAGE_TOKENS_FILE = Path(__file__).parent / "page_tokens.json"


class RateLimiter:
    """Thread-safe rate limiter with exponential backoff."""

    def __init__(self, requests_per_minute: int = 30):
        self.min_interval = 60.0 / requests_per_minute
        self.last_request = 0
        self.lock = Lock()
        self.backoff = 1.0
        self.total_requests = 0
        self.rate_limit_hits = 0

    def acquire(self):
        """Wait for rate limit slot."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_request
            wait_time = self.min_interval * self.backoff

            if elapsed < wait_time:
                time.sleep(wait_time - elapsed)

            self.last_request = time.time()
            self.total_requests += 1

    def on_rate_limit(self):
        """Increase backoff on rate limit hit."""
        with self.lock:
            self.backoff = min(self.backoff * 2, 10)
            self.rate_limit_hits += 1
            print(f"  [Rate limit] Backing off: {self.backoff:.1f}x")

    def on_success(self):
        """Gradually reduce backoff on success."""
        with self.lock:
            self.backoff = max(1.0, self.backoff * 0.95)

    def get_stats(self) -> dict:
        """Return rate limiter statistics."""
        return {
            "total_requests": self.total_requests,
            "rate_limit_hits": self.rate_limit_hits,
            "current_backoff": self.backoff
        }


def fetch_with_retry(url: str, params: dict, rate_limiter: RateLimiter,
                     max_retries: int = 3) -> dict | None:
    """Fetch with rate limiting and retry logic."""
    for attempt in range(max_retries):
        rate_limiter.acquire()

        try:
            resp = requests.get(url, params=params, timeout=30)

            if resp.status_code == 429:
                rate_limiter.on_rate_limit()
                wait_time = 5 * (attempt + 1)
                print(f"  [429] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
                continue

            if resp.status_code != 200:
                error_data = resp.json() if resp.text else {}
                error_msg = error_data.get("error", {}).get("message", f"HTTP {resp.status_code}")
                print(f"  [Error] {error_msg}")
                return None

            rate_limiter.on_success()
            return resp.json()

        except requests.exceptions.Timeout:
            print(f"  [Timeout] Attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"  [Network Error] {e}")
            if attempt < max_retries - 1:
                time.sleep(2)

    return None


def normalize_post_id(post_id: str) -> str:
    """Normalize post ID by stripping page ID prefix."""
    post_id_str = str(post_id)
    if '_' in post_id_str:
        return post_id_str.split('_')[-1]
    return post_id_str


def fetch_post_details(post_id: str, token: str, rate_limiter: RateLimiter) -> dict:
    """Fetch detailed metrics for a single post (optimized - single API call)."""
    url = f"{BASE_URL}/{post_id}"
    params = {
        "access_token": token,
        "fields": "reactions.summary(total_count),comments.summary(total_count),shares,attachments{media_type}"
    }

    data = fetch_with_retry(url, params, rate_limiter)

    if not data:
        return {
            "reactions_total": 0,
            "comments_count": 0,
            "shares_count": 0,
            "post_type": "TEXT"
        }

    # Extract metrics
    reactions_total = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
    comments_count = data.get("comments", {}).get("summary", {}).get("total_count", 0)
    shares_count = data.get("shares", {}).get("count", 0)

    # Determine post type
    attachments = data.get("attachments", {}).get("data", [])
    if attachments:
        media_type = attachments[0].get("media_type", "").lower()
        if media_type == "video":
            post_type = "VIDEO"
        elif media_type == "photo":
            post_type = "IMAGE"
        elif media_type == "album":
            post_type = "IMAGE"
        else:
            post_type = "TEXT"
    else:
        post_type = "TEXT"

    return {
        "reactions_total": reactions_total,
        "comments_count": comments_count,
        "shares_count": shares_count,
        "post_type": post_type
    }


def fetch_page_posts(page_id: str, token: str, rate_limiter: RateLimiter,
                     days: int = 60) -> list:
    """Fetch all posts for a page within date range."""
    posts = []
    since_date = datetime.now() - timedelta(days=days)

    url = f"{BASE_URL}/{page_id}/posts"
    params = {
        "access_token": token,
        "fields": "id,message,created_time,permalink_url",
        "limit": 100,
        "since": int(since_date.timestamp())
    }

    while True:
        data = fetch_with_retry(url, params, rate_limiter)

        if not data or "error" in data:
            break

        page_posts = data.get("data", [])
        posts.extend(page_posts)

        # Check for next page
        next_url = data.get("paging", {}).get("next")
        if not next_url:
            break

        url = next_url
        params = {}  # Next URL includes all params

    return posts


def fetch_page_info(page_id: str, token: str, rate_limiter: RateLimiter) -> dict:
    """Fetch page info including follower counts."""
    url = f"{BASE_URL}/{page_id}"
    params = {
        "access_token": token,
        "fields": "id,name,fan_count,followers_count,category,link"
    }

    data = fetch_with_retry(url, params, rate_limiter)

    if not data:
        return {}

    return {
        "fan_count": data.get("fan_count", 0),
        "followers_count": data.get("followers_count", 0),
        "category": data.get("category"),
        "link": data.get("link")
    }


def fetch_single_page(label: str, page_data: dict, rate_limiter: RateLimiter,
                      days: int = 60) -> dict:
    """Fetch all data for a single page."""
    page_id = page_data.get("page_id")
    page_name = page_data.get("page_name", label)
    token = page_data.get("page_access_token")

    if not token or not page_id:
        return {"label": label, "error": "Missing token or page_id", "posts": []}

    # Fetch page info (followers, etc.)
    print(f"  [{page_name}] Fetching page info...")
    page_info = fetch_page_info(page_id, token, rate_limiter)
    page_data.update(page_info)

    if page_info.get("followers_count"):
        print(f"  [{page_name}] Followers: {page_info['followers_count']:,}")

    print(f"  [{page_name}] Fetching posts list...")

    # Get posts list
    posts = fetch_page_posts(page_id, token, rate_limiter, days)

    if not posts:
        print(f"  [{page_name}] No posts found")
        return {"label": label, "page_data": page_data, "posts": [], "error": None}

    print(f"  [{page_name}] Found {len(posts)} posts, fetching details...")

    # Get details for each post
    detailed_posts = []
    for i, post in enumerate(posts):
        print(f"  [{page_name}] Post {i+1}/{len(posts)}", end="\r")

        details = fetch_post_details(post["id"], token, rate_limiter)

        detailed_posts.append({
            "post_id": post["id"],
            "message": (post.get("message") or "")[:500],
            "created_time": post.get("created_time"),
            "permalink": post.get("permalink_url"),
            **details
        })

    print(f"  [{page_name}] Done! {len(detailed_posts)} posts processed")

    return {
        "label": label,
        "page_data": page_data,
        "posts": detailed_posts,
        "error": None
    }


def save_to_database(results: dict) -> int:
    """Save fetched data to SQLite database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    total_saved = 0

    for label, result in results.items():
        if result.get("error"):
            continue

        page_data = result.get("page_data", {})
        posts = result.get("posts", [])

        if not page_data or not posts:
            continue

        # Update page with follower counts
        cursor.execute("""
            INSERT OR REPLACE INTO pages
            (page_id, page_name, fan_count, followers_count, category, link, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            page_data["page_id"],
            page_data["page_name"],
            page_data.get("fan_count", 0),
            page_data.get("followers_count", 0),
            page_data.get("category"),
            page_data.get("link"),
            now
        ))

        # Save posts
        for post in posts:
            normalized_id = normalize_post_id(post["post_id"])

            # Calculate engagement metrics
            reactions = post.get("reactions_total", 0)
            comments = post.get("comments_count", 0)
            shares = post.get("shares_count", 0)
            total_engagement = reactions + comments + shares

            # PES = (Reactions * 1) + (Comments * 2) + (Shares * 3)
            pes = (reactions * 1) + (comments * 2) + (shares * 3)

            # Viral coefficient = Shares / Total Engagement
            viral = (shares / total_engagement) if total_engagement > 0 else 0

            cursor.execute("""
                INSERT OR REPLACE INTO posts
                (post_id, page_id, title, permalink, post_type, publish_time,
                 reactions_total, comments_count, shares_count, total_engagement,
                 pes, viral_coefficient, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                normalized_id,
                page_data["page_id"],
                post.get("message", "")[:200],
                post.get("permalink"),
                post.get("post_type"),
                post.get("created_time"),
                reactions,
                comments,
                shares,
                total_engagement,
                round(pes, 2),
                round(viral, 4),
                now
            ))
            total_saved += 1

    conn.commit()
    conn.close()

    return total_saved


def save_progress(results: dict, completed_pages: list):
    """Save progress checkpoint."""
    progress = {
        "timestamp": datetime.now().isoformat(),
        "completed_pages": completed_pages,
        "results": {
            label: {
                "posts_count": len(r.get("posts", [])),
                "error": r.get("error")
            }
            for label, r in results.items()
        }
    }

    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def load_progress() -> dict | None:
    """Load progress from checkpoint file."""
    if not PROGRESS_FILE.exists():
        return None

    try:
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    except:
        return None


def main():
    parser = argparse.ArgumentParser(description="Smart Facebook Data Fetcher")
    parser.add_argument("--days", type=int, default=60, help="Days of data to fetch (default: 60)")
    parser.add_argument("--workers", type=int, default=3, help="Parallel workers (default: 3)")
    parser.add_argument("--rpm", type=int, default=30, help="Requests per minute (default: 30)")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    args = parser.parse_args()

    print("=" * 60)
    print("Smart Facebook Data Fetcher")
    print("=" * 60)
    print(f"Days: {args.days} | Workers: {args.workers} | RPM: {args.rpm}")
    print()

    # Load page tokens
    if not PAGE_TOKENS_FILE.exists():
        print(f"ERROR: {PAGE_TOKENS_FILE} not found")
        return

    with open(PAGE_TOKENS_FILE) as f:
        pages = json.load(f)

    print(f"Found {len(pages)} pages to fetch")

    # Check for resume
    completed_pages = []
    if args.resume:
        progress = load_progress()
        if progress:
            completed_pages = progress.get("completed_pages", [])
            print(f"Resuming from checkpoint: {len(completed_pages)} pages already done")

    # Filter out completed pages
    remaining_pages = {k: v for k, v in pages.items() if k not in completed_pages}

    if not remaining_pages:
        print("All pages already fetched!")
        return

    print(f"Fetching {len(remaining_pages)} pages...")

    # Initialize rate limiter
    rate_limiter = RateLimiter(requests_per_minute=args.rpm)

    # Process pages in parallel batches
    results = {}
    start_time = time.time()
    page_items = list(remaining_pages.items())

    for batch_start in range(0, len(page_items), args.workers):
        batch = page_items[batch_start:batch_start + args.workers]
        batch_num = batch_start // args.workers + 1
        total_batches = (len(page_items) + args.workers - 1) // args.workers

        print(f"\n[Batch {batch_num}/{total_batches}] {[p[0] for p in batch]}")

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(
                    fetch_single_page,
                    label,
                    data,
                    rate_limiter,
                    args.days
                ): label
                for label, data in batch
            }

            for future in as_completed(futures):
                label = futures[future]
                try:
                    result = future.result()
                    results[label] = result
                    completed_pages.append(label)

                    if result.get("error"):
                        print(f"  [{label}] ERROR: {result['error']}")
                    else:
                        print(f"  [{label}] Completed: {len(result.get('posts', []))} posts")
                except Exception as e:
                    print(f"  [{label}] EXCEPTION: {e}")
                    results[label] = {"label": label, "error": str(e), "posts": []}

        # Save checkpoint after each batch
        save_progress(results, completed_pages)
        print(f"  [Checkpoint saved]")

    # Save to database
    print("\nSaving to database...")
    total_saved = save_to_database(results)

    # Cleanup progress file on success
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    # Summary
    elapsed = time.time() - start_time
    stats = rate_limiter.get_stats()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Pages processed: {len(results)}")
    print(f"Posts saved: {total_saved}")
    print(f"Time elapsed: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"API requests: {stats['total_requests']}")
    print(f"Rate limit hits: {stats['rate_limit_hits']}")
    print(f"Database: {DATABASE_PATH}")
    print("\n[DONE]")


if __name__ == "__main__":
    main()
