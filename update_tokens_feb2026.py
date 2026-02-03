#!/usr/bin/env python3
"""
Update page_tokens.json with new long-lived tokens.
Converts short-lived tokens from Feb 2026 to long-lived tokens.
"""

import json
import requests
import time

APP_ID = "3716866408461062"
APP_SECRET = "aba36f1a3d85461984b8b94eab54080a"

# New short-lived tokens received (Feb 2026)
NEW_SHORT_TOKENS = {
    "Tanya": "EAA00eGX0MwYBQvitdgsKgdr4WoJ3cWeYI5oFAK0HViZAqzwifUT2xZBys1EavrkQ0MzP5N0RJL4MeQzwP0ZBLrHgNVJf2mFEENZCFMSTvZC0jVbh4zIl4y1NkOHPB9onuUY5TjvhodiB3T1SOiRuEsZAgs1zrQHZBWVo2LOe4eF1y6iUeZAo1ejVMBWZCY2ZBkVT7s8E0ejQncygOcaa6lMKtMqWCVExZAeTYiaNiWw1EkdVEwZD",
    "Elise": "EAA00eGX0MwYBQlcZAjnCZCJ3ZAWsiOlIAqq8898v4gbua1IytJN0S06p61TOvZBVAZCuNXci250kLtT46YSU8orOy1tUiaLAwzTnFn2YDwlg0PDy6YYgyrLPhgN1yr1soZCu0caiBgBIyeujpG7WNw4oLuElcj4827KOMY42sZCstTyUcdzSRGuRK0ZCwce2mGFtLOVsJ0Ljb7DGxZCrNCLDVgPb1MDXrWAVDZCSUFmgexy5EZD",
    "Star": "EAA00eGX0MwYBQtqrmgjbeWZAAZAth3zj0gMyG4qopfIkp89ZCEvTZCxywZCFjs26tKUNGlJWZCIVkpgOkIQgVc7B0yWNRAiTwDkKZAiJ5TQx6s3U9PDMqAWbxYZBamtQbO6ct7Rn6IKuOztTFG8i5m9pzwRZBkP3sZCSZBPnqSDR26hFDnrN2HgJUcmhUzKfN6yOYAdZCiiUdI9x9eTkQ5h4YzKwUcE7wQVxbNKmAtFtexiwTKgZD",
    "Charm": "EAA00eGX0MwYBQlkGa91ZBvTkuqF9odBlgNbcZAEB8J5UGCfO7ZB1p4NmXylXizAT5Qtsu5QtMowoxKNT1H5gMPHffoxQ2MYJi8VacanXE2yIzZCA4E7xu7jOdzVaf7Iru39mlnIjyQB5cFaLvyahJZBpfbxzlOjZCU2EXcgvwZAAdksHZA0EWwL68jxTdAOPH7ZC98wSxtZBa75JXZCxX25wTgn8lzJHBmzhT3n1rSzCjeql6sZD",
    "Shann": "EAA00eGX0MwYBQhCZALHGfSfLzrZCloDcKsvixb7jvcYW9C4IavJ734NK6R9ARp6htRvS8CRrBZCcYRQZBxB468ge2yEhZA1J63xMZCwuZAmh8M9ZCo4T1cVgCWYQFDkSQ5oSO445E4D9aj1Anw5JzB8MxVDbQDZCCo1ZAsc9FCJhYJfvyBLq6L7hUvisHrckaEq169mxCC3WlE84KEirM7L6T4bgCKE0MO4Xkz45AnyzpZByYcZD",
    "Evo": "EAA00eGX0MwYBQoLo49SCZAd20bcACkZAEd2sXJk4fpPEQrdTt7GEhoHHvBwTbeghbcbBy20JBgSsBdyfRqjWzFAX2nkK60cYuplYVONME8nWZAS7ZBN8V6eKpIBazYZAJybPflR6K2ryHs5PgKFLqVMYXiyqPvquGZBTEZCzDZCcPmk8fxEuAZBXHRRdqJkL0Pyr902ZCbM3AZC9ZAzn4Q77ZAYxZCFl7oyZC5DMtpnsRjd2GBiQRgZD",
    "PapaJoe": "EAA00eGX0MwYBQplhsnW56fZBdWAQ52ZAqTB5dy6jkJ34SQkVxQzMELStReXhKKnHg5jmbuIZBfpyEB3qUlNfkwCbGBXicGf2ZCKotiB19ZAxfwyFkUegPgjoxNAMnlI8E6tQkZAelZBeTqYi870p1DffubG5m4N82JrcQGy9vDjSXwKV4ZBksVAbTKZCfTaPNAHiXjw1FXcg0VX9beF2Ya4PRtxz4YKqk4s3eP6HB5QNUObkZD",
    "Lance": "EAA00eGX0MwYBQqT3zbdKhnDOZCyr8iZCqb7mRyQyvtc9exJ0teNJsVN1hoCZADY83HSx3Md8hYVnzXVK92J7aMsEaZAv2vTvT6JBXrauyRYzLZA03Lj1a7tQWlSK2HuQyRNLmfrs9jz1Vr53tEXXUgm5JiXSXuz7u1trzgta5vb0JZCx2yhZBD0PlPshAIbPLfyo6IdBc9CALaP8Abm3Fm4JZA13yKJjyNOgkeKzdkYWsIIZD",
    "Jedi": "EAA00eGX0MwYBQsuf50Bwf0vCLWZCfMlC51snaB0ye4psXZATQ8CXFK8gJkKMxZCGuSgvnVFvImbgdkD6jzQbm6EGcPsOlSXtbyDffttJTCdRj7qYQEWYEn8yVDnaF4Opz1ZB3ko71SRuLRnaGbzEKwGO3InEY6W5y6BnvHkfAvZARHKMDzIZCtdDitwtu0sQTlWXaJSFYZC4TZAsZCk9Y3d3ZBKgAFDpZCRR1hAieYdP7OFeH0ZD",
    "Ligaya": "EAA00eGX0MwYBQuVNYBgMabyoLaIVkLIK0GmKgZC9qWQCMGykT1QQH9ZBqzUmpwz4THGueDk470xrhwR62KSqerCQ2yD2ZCewEnOUg38VO4EyoqupECzsLGisUcytD1ZAZCZAqIMmG1nA9MrMRgw70jfhYM7Aw2B3NdJdAs2vAecZBZCQk1dznQ1nfXUTRBAjhJYwgXs3DhUE3VBVPllpMmgIbA4djQmnSwLLNcMH1IM4SXwZD",
    "Sabbie": "EAA00eGX0MwYBQuBrLXNu38ijH8oEU22GB7ZCvguBU14k7AOWqmgy3ZCZAYWwrkVtBai3qNBiByoVlyei2gNFyQtym6K9vY2tasXdaaZAwf73doWI0hQNi8NHFkWQlVLTvhXrJ2MZBHQgRgx7noZAcehfYorN5L1L16W8cQHcs1JjSwoNANTTHGzYwnCoJZAdSVdyWcLqEsZAx4lu4Q6LtC0sXn4SLWHPsfMCoDzGxzOtwVgZD",
    "Alexchoozy": "EAA00eGX0MwYBQlpBzaZBxFBFp20zLEw8YK8oSuuYOweLWaiZCF0qQ5iFbvnO5LGIHhmONuvspmyfcZBjbnZAsPe5UPlZAC1QzRKvKlmJhtQZC1xVOXgSpKKGFUfu1DZCVBj0Pbp5ZCpzdZCPPlSODEPMNXpFfeTAlZChwMjMGJPJgQrAxJU891vl92FxkZAZA0dp18RTaQ8NPS54yHRAUjviIEDX35hQq29wTIclR19j6MHSmxgZD",
    "Ikay": "EAA00eGX0MwYBQpb49St41LZCu4rMEVKigMDdLftf9uke8elKYgLDPL9ZBzSapNuXa4EtokbZAZBK4nOwY5SSqVuXAHN9PZCPGnvzMHDtMTD0CowuQCZAbgX32iPD95ALeJ2xxPNjuXi24G0XjvlqI8gSUC1jmRDIh2DErMYbmnTK3ew7pG7dGMnq1QRLbZC017ZBTaB40PkVjUSI3ZCv2RbhXH1aE5cFz69ehMBUpZAZCCAcZBEZD",
    "Geoff": "EAA00eGX0MwYBQuLCITpr1mmjiqnKJSYt28riyMNlr9VvBy8xOITpfvyMKn7BgdETmGslm0qqGZBHwYNq8bfqljx6TFQQgq51BpePTbtEWvOFUdaUlit6TKTubogtCZCmNnCrZCX2ZCtNpQh2ZBVEJbiOn4QHylZA5FpXiDoO0U7cZC0DroN4BBeG6HaeY6pDn3UuEa2jdaAvjJO7LkPLrSf2vGfbK5tHqGrbhkihuG9zyIZD",
    "Drae": "EAA00eGX0MwYBQnYOJrG1kvLBCuOiPhzPd7UgQArjFzwo9VOmafsbP3iZBEl5FbwAueL6o0hZAKozhGRaHeX51py3p73PTdQJIYYUZB7WI1sX9E21ZC6sKLfUh165mEHvBuP4KZBOxU53V0b51fYIZBLoNGGFzCfv4JjJrtxrsNKWgRx6bUbbnxuP9xZCOEmpR3NZALs3Fe2S9LtW3saD2DbniOQum3pRs2y4DiS6l2lnLAZDZD",
    "Zia": "EAA00eGX0MwYBQoVybV8t4IvWtDIS1gyMKpGtrpy4r2v55HwIPwDFXLiBTdm2BnvMWAd5XbZCZBu8WN7Mai8rhSgUzv5zQQmQlIAx4J6ncUPYjAZAu7pkGhBfdcIbSUeeBiAJPqvfAn5SOtLY3vy9P7OwF8s8d2nk5XtZAZC935Bi1yUlwqY9hzufAeVqjgT1SJIUVXCfNp4I7hm1aSGuLGU0OUNMwwLhNKngu4VLkaAZDZD",
}

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
            expires_in = data.get("expires_in", 5184000)  # Default 60 days
            return data["access_token"], expires_in
        else:
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            print(f"    Error: {error_msg}")
            return None, None
    except Exception as e:
        print(f"    Request error: {e}")
        return None, None


def test_token_permissions(token, page_name):
    """Test if token can fetch posts with engagement data."""
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
    # Load existing page_tokens.json
    with open("page_tokens.json", "r") as f:
        page_tokens = json.load(f)

    print("=" * 70)
    print("STEP 1: Converting short-lived tokens to long-lived tokens")
    print("=" * 70)

    successful = 0
    failed = 0

    for page_name, short_token in NEW_SHORT_TOKENS.items():
        print(f"\n[{page_name}]")

        # Handle name mismatch (Elise vs Ellise in JSON)
        json_key = page_name
        if page_name == "Elise":
            json_key = "Elise"  # Check if exists
            if json_key not in page_tokens:
                # Try alternative spellings
                for key in page_tokens.keys():
                    if "lis" in key.lower() or "lise" in key.lower():
                        json_key = key
                        break

        if json_key not in page_tokens:
            print(f"  WARNING: '{page_name}' not found in page_tokens.json, skipping...")
            failed += 1
            continue

        # Convert to long-lived token
        long_token, expires_in = get_long_lived_token(short_token)

        if long_token:
            print(f"  Token converted successfully!")
            print(f"  Expires in: {expires_in} seconds (~{expires_in // 86400} days)")

            # Update both user_access_token and page_access_token
            page_tokens[json_key]["user_access_token"] = long_token
            page_tokens[json_key]["page_access_token"] = long_token
            page_tokens[json_key]["expires_in"] = expires_in
            successful += 1
        else:
            print(f"  FAILED to convert token!")
            failed += 1

        # Rate limiting
        time.sleep(0.5)

    # Save updated tokens
    with open("page_tokens.json", "w") as f:
        json.dump(page_tokens, f, indent=2)

    print("\n" + "=" * 70)
    print(f"CONVERSION COMPLETE: {successful} successful, {failed} failed")
    print("=" * 70)

    # Step 2: Test token permissions
    print("\n" + "=" * 70)
    print("STEP 2: Testing token permissions (engagement data access)")
    print("=" * 70)

    # Reload updated tokens
    with open("page_tokens.json", "r") as f:
        page_tokens = json.load(f)

    working = 0
    not_working = 0

    for page_name, data in page_tokens.items():
        token = data.get("page_access_token", "")
        success, result = test_token_permissions(token, page_name)

        if success:
            print(f"  [OK] {page_name}: {result}")
            working += 1
        else:
            print(f"  [FAIL] {page_name}: {result}")
            not_working += 1

        time.sleep(0.3)

    print("\n" + "=" * 70)
    print(f"PERMISSION TEST: {working} working, {not_working} failed")
    print("=" * 70)

    if not_working == 0:
        print("\nAll tokens have proper permissions!")
        print("You can now run: python fetch_date_posts.py 2026-02-02")
    else:
        print(f"\nWARNING: {not_working} tokens failed permission test!")


if __name__ == "__main__":
    main()
