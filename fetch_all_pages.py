#!/usr/bin/env python3
"""Fetch data from all 5 Facebook pages in PARALLEL and store in database."""

import json
import sqlite3
import requests
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from facebook_api import FacebookAPI, calculate_engagement_metrics


def classify_post_type(post):
    """Classify post type based on type and status_type fields."""
    post_type = post.get("type", "").lower()
    status_type = post.get("status_type", "").lower()

    if post_type == "video":
        if "reel" in status_type:
            return "REEL"
        return "VIDEO"
    elif post_type == "photo":
        return "IMAGE"
    elif post_type == "link":
        return "LINK"
    elif status_type == "added_photos":
        return "IMAGE"
    elif status_type == "added_video":
        return "VIDEO"
    elif status_type == "shared_story":
        return "SHARE"
    else:
        return "TEXT"


# Load page tokens
with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)

DATABASE_PATH = "data/juanbabes_analytics.db"


def init_database():
    """Initialize the database with updated schema."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pages (
            page_id TEXT PRIMARY KEY,
            page_name TEXT NOT NULL,
            fan_count INTEGER,
            followers_count INTEGER,
            category TEXT,
            link TEXT,
            is_competitor INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            page_id TEXT NOT NULL,
            title TEXT,
            permalink TEXT,
            post_type TEXT,
            publish_time TEXT,
            reactions_total INTEGER DEFAULT 0,
            reactions_like INTEGER DEFAULT 0,
            reactions_love INTEGER DEFAULT 0,
            reactions_haha INTEGER DEFAULT 0,
            reactions_wow INTEGER DEFAULT 0,
            reactions_sad INTEGER DEFAULT 0,
            reactions_angry INTEGER DEFAULT 0,
            comments_count INTEGER DEFAULT 0,
            shares_count INTEGER DEFAULT 0,
            page_comments INTEGER DEFAULT 0,
            has_page_comment INTEGER DEFAULT 0,
            pes REAL DEFAULT 0,
            qes REAL DEFAULT 0,
            viral_coefficient REAL DEFAULT 0,
            total_engagement INTEGER DEFAULT 0,
            fetched_at TEXT,
            FOREIGN KEY (page_id) REFERENCES pages(page_id)
        )
    """)

    conn.commit()
    return conn


def fetch_page_posts(token, page_id, days_back=90):
    """Fetch all posts from a page."""
    since_date = datetime.now() - timedelta(days=days_back)
    # Only basic fields - type/status_type/shares are deprecated
    fields = "id,message,created_time,permalink_url"

    all_posts = []
    url = f"https://graph.facebook.com/v21.0/{page_id}/posts"
    params = {
        "access_token": token,
        "fields": fields,
        "limit": 100,
        "since": int(since_date.timestamp())
    }

    while True:
        try:
            resp = requests.get(url, params=params)
            data = resp.json()

            if "error" in data:
                return {"error": data['error'].get('message', 'Unknown')}

            posts = data.get("data", [])
            all_posts.extend(posts)

            paging = data.get("paging", {})
            next_url = paging.get("next")

            if next_url:
                url = next_url
                params = {}
            else:
                break

            time.sleep(0.1)

        except Exception as e:
            return {"error": str(e)}

    return all_posts


def process_post(token, post, page_id):
    """Process a single post to get reactions/comments/shares/type."""
    post_id = post["id"]

    try:
        url = f"https://graph.facebook.com/v21.0/{post_id}"
        params = {
            "access_token": token,
            "fields": "reactions.summary(total_count),comments.summary(total_count),shares,attachments{media_type}"
        }
        resp = requests.get(url, params=params)
        data = resp.json()
        total_reactions = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments_count = data.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares_count = data.get("shares", {}).get("count", 0)

        # Get post type from attachments
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
    except:
        total_reactions = 0
        comments_count = 0
        shares_count = 0
        post_type = "TEXT"

    reactions = {"like": total_reactions, "love": 0, "haha": 0, "wow": 0, "sad": 0, "angry": 0}

    metrics = calculate_engagement_metrics({
        "reactions": reactions,
        "comments_count": comments_count,
        "shares_count": shares_count
    })

    return {
        "post_id": post_id,
        "message": (post.get("message", "") or "")[:500],
        "created_time": post.get("created_time"),
        "permalink": post.get("permalink_url"),
        "post_type": post_type,
        "reactions": reactions,
        "reactions_total": total_reactions,
        "comments_count": comments_count,
        "shares_count": shares_count,
        "page_comments": 0,
        "has_page_comment": False,
        "metrics": metrics
    }


def fetch_single_page(label, data):
    """Fetch all data for a single page. Returns (page_data, posts_data)."""
    if "error" in data:
        return {"label": label, "error": data['error'], "posts": []}

    page_id = data.get("page_id")
    page_name = data.get("page_name", label)
    token = data.get("page_access_token")

    if not token or not page_id:
        return {"label": label, "error": "Missing token or page_id", "posts": []}

    print(f"  [{page_name}] Fetching posts...")

    # Fetch posts
    posts = fetch_page_posts(token, page_id, days_back=90)

    if isinstance(posts, dict) and "error" in posts:
        return {"label": label, "page_data": data, "error": posts["error"], "posts": []}

    print(f"  [{page_name}] Found {len(posts)} posts, processing...")

    # Process posts in parallel (5 at a time to avoid rate limits)
    processed_posts = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_post, token, post, page_id): post for post in posts}
        for future in as_completed(futures):
            try:
                result = future.result()
                processed_posts.append(result)
            except Exception as e:
                pass

    print(f"  [{page_name}] Done! {len(processed_posts)} posts processed")

    return {
        "label": label,
        "page_data": data,
        "posts": processed_posts,
        "error": None
    }


def save_results(conn, results):
    """Save all results to database."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    total_posts = 0

    for result in results:
        if result.get("error"):
            continue

        page_data = result.get("page_data", {})
        posts = result.get("posts", [])

        # Save page
        cursor.execute("""
            INSERT OR REPLACE INTO pages
            (page_id, page_name, fan_count, followers_count, category, link, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM pages WHERE page_id = ?), ?), ?)
        """, (
            page_data["page_id"],
            page_data["page_name"],
            page_data.get("fan_count"),
            page_data.get("followers_count"),
            page_data.get("category"),
            page_data.get("link"),
            page_data["page_id"],
            now,
            now
        ))

        # Save posts
        for post_data in posts:
            reactions = post_data.get("reactions", {})
            metrics = post_data.get("metrics", {})

            cursor.execute("""
                INSERT OR REPLACE INTO posts
                (post_id, page_id, title, permalink, post_type, publish_time,
                 reactions_total, reactions_like, reactions_love, reactions_haha,
                 reactions_wow, reactions_sad, reactions_angry,
                 comments_count, shares_count, page_comments, has_page_comment,
                 pes, qes, viral_coefficient, total_engagement, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_data["post_id"],
                page_data["page_id"],
                post_data.get("message", "")[:200],
                post_data.get("permalink"),
                post_data.get("post_type"),
                post_data.get("created_time"),
                post_data.get("reactions_total", 0),
                reactions.get("like", 0),
                reactions.get("love", 0),
                reactions.get("haha", 0),
                reactions.get("wow", 0),
                reactions.get("sad", 0),
                reactions.get("angry", 0),
                post_data.get("comments_count", 0),
                post_data.get("shares_count", 0),
                post_data.get("page_comments", 0),
                1 if post_data.get("has_page_comment") else 0,
                metrics.get("pes", 0),
                metrics.get("qes", 0),
                metrics.get("viral_coefficient", 0),
                metrics.get("total_engagement", 0),
                now
            ))
            total_posts += 1

    conn.commit()
    return total_posts


def main():
    print("=" * 60)
    print("JuanBabes - Fetching Data from 5 Facebook Pages (PARALLEL)")
    print("=" * 60)

    # Initialize database
    print("\nInitializing database...")
    conn = init_database()

    # Fetch all pages in parallel
    print("\nFetching all pages in parallel...")
    start_time = time.time()

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_single_page, label, data): label
                   for label, data in PAGE_TOKENS.items()}

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            if result.get("error"):
                print(f"  [{result['label']}] ERROR: {result['error']}")

    # Save all results
    print("\nSaving to database...")
    total_posts = save_results(conn, results)
    conn.close()

    elapsed = time.time() - start_time

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total pages processed: {len([r for r in results if not r.get('error')])}")
    print(f"Total posts saved: {total_posts}")
    print(f"Time elapsed: {elapsed:.1f} seconds")
    print(f"Database: {DATABASE_PATH}")
    print("\n[DONE] Data fetch complete!")


if __name__ == "__main__":
    main()
