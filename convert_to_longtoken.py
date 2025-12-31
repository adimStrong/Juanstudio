#!/usr/bin/env python3
"""
Convert short-lived page tokens to long-lived tokens and get page IDs.
"""

import json
import requests

APP_ID = "2285430771870998"
APP_SECRET = "20c0ffb9eb57a8742eb1720c87172d63"

def get_long_lived_token(short_token):
    """Convert short-lived token to long-lived token."""
    url = "https://graph.facebook.com/v21.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "fb_exchange_token": short_token
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "access_token" in data:
            return data["access_token"]
        else:
            print(f"Error: {data.get('error', {}).get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Request error: {e}")
        return None


def get_page_id(token):
    """Get page ID from token."""
    url = "https://graph.facebook.com/v21.0/me"
    params = {
        "access_token": token,
        "fields": "id,name"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "id" in data:
            return data["id"], data.get("name", "Unknown")
        else:
            print(f"Error getting page ID: {data.get('error', {}).get('message', 'Unknown')}")
            return None, None
    except Exception as e:
        print(f"Request error: {e}")
        return None, None


def main():
    # Load raw tokens
    with open("page_tokens_raw.json", "r") as f:
        raw_tokens = json.load(f)

    # Convert each token
    converted = {}

    for label, data in raw_tokens.items():
        page_name = data["page_name"]
        short_token = data["page_access_token"]

        print(f"\nProcessing: {page_name}")

        # Get page ID first (using short token)
        page_id, api_name = get_page_id(short_token)
        if page_id:
            print(f"  Page ID: {page_id}")
            print(f"  API Name: {api_name}")
        else:
            print(f"  Failed to get page ID, skipping...")
            continue

        # Convert to long-lived token
        long_token = get_long_lived_token(short_token)
        if long_token:
            print(f"  Token converted successfully!")
            converted[label] = {
                "page_id": page_id,
                "page_name": page_name,
                "page_access_token": long_token
            }
        else:
            print(f"  Failed to convert token, using original")
            converted[label] = {
                "page_id": page_id,
                "page_name": page_name,
                "page_access_token": short_token
            }

    # Save converted tokens
    with open("page_tokens.json", "w") as f:
        json.dump(converted, f, indent=4)

    print(f"\n{'='*60}")
    print(f"Converted {len(converted)} tokens")
    print(f"Saved to page_tokens.json")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
