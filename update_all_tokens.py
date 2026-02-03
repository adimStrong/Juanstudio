#!/usr/bin/env python3
"""
Update all page tokens with new short-lived tokens, convert to long-lived.
"""

import json
import requests
import time

APP_ID = "3716866408461062"
APP_SECRET = "aba36f1a3d85461984b8b94eab54080a"

# New tokens provided by user
NEW_TOKENS = {
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
            expires_in = data.get("expires_in", 5184000)
            return data["access_token"], expires_in
        else:
            error_msg = data.get('error', {}).get('message', 'Unknown error')
            return None, error_msg
    except Exception as e:
        return None, str(e)


def test_engagement(token, page_name):
    """Test if token can fetch engagement data."""
    url = "https://graph.facebook.com/v21.0/me/posts"
    params = {
        "access_token": token,
        "fields": "id,reactions.summary(true),comments.summary(true),shares",
        "limit": 1
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "error" in data:
            return False, data["error"].get("message", "Unknown error")

        if "data" in data and len(data["data"]) > 0:
            post = data["data"][0]
            r = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
            c = post.get("comments", {}).get("summary", {}).get("total_count", 0)
            s = post.get("shares", {}).get("count", 0)
            return True, f"R:{r} C:{c} S:{s}"
        else:
            return True, "No posts (token OK)"
    except Exception as e:
        return False, str(e)


def main():
    # Load existing tokens
    with open("page_tokens.json", "r") as f:
        page_tokens = json.load(f)

    print("=" * 70)
    print("Converting tokens and testing engagement permissions")
    print("=" * 70)

    converted = 0
    working = 0

    for name, short_token in NEW_TOKENS.items():
        print(f"\n[{name}]")

        # Convert to long-lived
        long_token, result = get_long_lived_token(short_token)

        if long_token:
            print(f"  Converted to long-lived (~60 days)")

            # Test engagement
            success, eng_result = test_engagement(long_token, name)
            if success:
                print(f"  [OK] Engagement: {eng_result}")
                working += 1
            else:
                print(f"  [FAIL] {eng_result}")

            # Update in page_tokens
            if name in page_tokens:
                page_tokens[name]["page_access_token"] = long_token
                page_tokens[name]["user_access_token"] = long_token
                page_tokens[name]["expires_in"] = 5184000
                converted += 1
            else:
                print(f"  WARNING: {name} not found in page_tokens.json")
        else:
            print(f"  FAILED: {result}")

        time.sleep(0.3)

    # Save
    with open("page_tokens.json", "w") as f:
        json.dump(page_tokens, f, indent=2)

    print("\n" + "=" * 70)
    print(f"DONE: {converted} tokens converted, {working} have engagement permissions")
    print("=" * 70)

    if working < len(NEW_TOKENS):
        print(f"\nNOTE: {len(NEW_TOKENS) - working} pages need 'pages_read_engagement' permission")
        print("To fix: Re-authorize app with 'pages_read_engagement' permission for each page")


if __name__ == "__main__":
    main()
