#!/usr/bin/env python3
"""
Get page access tokens from user access token.
This properly fetches page tokens with engagement permissions.
"""

import json
import requests
import time

# Long-lived user access token
USER_TOKEN = "EAA00eGX0MwYBQlQwrtIqiqqHk6cV8lEqTZCqZAZBb4M2PImvYyCb8CLTAZAWDto7s7mMVKhR7fu5jk5LNf5Tr4pvuPaK7abRoksKDUcnTNHhHA8AU1pY8SVDqaZCSCZBGyTCICfjs8JGDMCczCBAPZCZBS3FsaEyG24GSnhaILmmsoYSr01MAnAfjutZATuwYnZAcK38GQ3ZCov4b7ZAPGMn7KqXizXsJm7Yu2luMg9fHJfBWONQUoAtDpYwHFBVZAsNz0qfwZATHbmrDAmhHBZC3PZBjF33"

def get_managed_pages():
    """Get all pages managed by the user with their page access tokens."""
    url = "https://graph.facebook.com/v21.0/me/accounts"
    params = {
        "access_token": USER_TOKEN,
        "fields": "id,name,access_token,fan_count,followers_count",
        "limit": 100
    }

    all_pages = []

    while url:
        try:
            response = requests.get(url, params=params)
            data = response.json()

            if "error" in data:
                print(f"Error: {data['error'].get('message', 'Unknown error')}")
                return []

            pages = data.get("data", [])
            all_pages.extend(pages)

            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}  # Clear params for next URL which has them embedded

        except Exception as e:
            print(f"Request error: {e}")
            break

    return all_pages


def test_page_token(token, page_name):
    """Test if page token can fetch engagement data."""
    url = "https://graph.facebook.com/v21.0/me/posts"
    params = {
        "access_token": token,
        "fields": "id,message,created_time,reactions.summary(true),comments.summary(true),shares",
        "limit": 1
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            return False, data["error"].get("message", "Unknown error")

        if "data" in data and len(data["data"]) > 0:
            post = data["data"][0]
            reactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
            comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = post.get("shares", {}).get("count", 0)
            return True, f"reactions={reactions}, comments={comments}, shares={shares}"
        else:
            return True, "No posts found (token works)"
    except Exception as e:
        return False, str(e)


def main():
    print("=" * 70)
    print("Fetching page tokens from user token...")
    print("=" * 70)

    # Get all managed pages
    pages = get_managed_pages()

    if not pages:
        print("No pages found or error occurred!")
        return

    print(f"\nFound {len(pages)} managed pages:\n")

    # Load existing page_tokens.json
    try:
        with open("page_tokens.json", "r") as f:
            page_tokens = json.load(f)
    except:
        page_tokens = {}

    # Map page IDs to labels in existing JSON
    page_id_to_label = {}
    for label, data in page_tokens.items():
        pid = data.get("page_id")
        if pid:
            page_id_to_label[pid] = label

    # Update tokens
    updated_count = 0
    new_count = 0

    for page in pages:
        page_id = page["id"]
        page_name = page["name"]
        page_token = page["access_token"]
        fan_count = page.get("fan_count", 0)
        followers_count = page.get("followers_count", 0)

        # Test the token
        success, result = test_page_token(page_token, page_name)
        status = "[OK]" if success else "[FAIL]"
        print(f"  {status} {page_name} (ID: {page_id})")
        print(f"       {result}")

        # Find matching label or create new entry
        if page_id in page_id_to_label:
            label = page_id_to_label[page_id]
            page_tokens[label]["page_access_token"] = page_token
            page_tokens[label]["user_access_token"] = page_token
            page_tokens[label]["fan_count"] = fan_count
            page_tokens[label]["followers_count"] = followers_count
            page_tokens[label]["expires_in"] = 5184000  # ~60 days
            updated_count += 1
        else:
            # Create new entry based on page name
            label = page_name.replace("Juankada ", "").replace("JuanKada ", "").replace("JUANKada Host ", "").strip()
            page_tokens[label] = {
                "user_access_token": page_token,
                "page_id": page_id,
                "page_name": page_name,
                "page_access_token": page_token,
                "fan_count": fan_count,
                "followers_count": followers_count,
                "expires_in": 5184000
            }
            new_count += 1

        time.sleep(0.2)

    # Save updated tokens
    with open("page_tokens.json", "w") as f:
        json.dump(page_tokens, f, indent=2)

    print("\n" + "=" * 70)
    print(f"DONE! Updated {updated_count} pages, added {new_count} new pages")
    print("Saved to page_tokens.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
