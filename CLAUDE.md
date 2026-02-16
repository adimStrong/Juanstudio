# JuanStudio Analytics - Project Guide

## Quick Reference
- **Live**: https://juanstudio-analytics.vercel.app
- **Repo**: https://github.com/adimStrong/Juanstudio.git
- **DB**: `data/juanstudio_analytics.db` (SQLite, ~2MB)
- **16 Juankada FB pages**, ~42 posts/day

## Architecture (DO NOT CHANGE)
```
Facebook API  ──→  fetch_missing_posts.py  ──→  SQLite (post identity + engagement)
                                                       ↓
Meta CSV Export ──→ import_manual_exports.py ──→  SQLite (UPDATE views/reach ONLY)
                                                       ↓
                                            export_static_data.py → analytics-v2.json
                                                       ↓
                                            git push → vercel --prod → Live
```

### CRITICAL RULES
1. **API is source of truth for posts.** Posts are CREATED only by `fetch_missing_posts.py` (API).
2. **CSV only updates views/reach.** `import_manual_exports.py` matches CSV rows to existing DB posts by `page_id + publish_time` and updates views/reach. It NEVER creates new posts.
3. **CSV Post IDs are ALL broken.** Meta exports them in scientific notation (`1.22187E+17`). Converting loses precision. 1,718 rows collapse to 228 wrong IDs. NEVER use CSV Post IDs.
4. **CSV times are UTC.** DB times are PHT (UTC+8) labeled as `+0000`. CSV importer adds +8h before matching.
5. **deploy = push.bat** which runs: cleanup → export → git push → vercel deploy.

## Daily Update Workflow
```
1. python fetch_missing_posts.py    # Fetch new posts from API (last 14 days)
2. python import_manual_exports.py  # Update views/reach from CSV (if new CSV exported)
3. python export_static_data.py     # Rebuild analytics JSON
4. push.bat                         # Deploy to Vercel
```

Or use the bat files:
- `update_api.bat` — steps 1+3
- `update_csv.bat` — steps 2+3
- `push.bat` — step 4 (includes cleanup + export)

## File Locations
- **CSV exports**: `exports/from content manual Export/*.csv`
- **Page tokens**: `page_tokens.json` (60-day expiry, 16 pages)
- **Frontend data**: `frontend/public/data/analytics-v2.json`
- **DB**: `data/juanstudio_analytics.db`

## Common Issues & Fixes

### "Post count suddenly jumped/dropped"
- Likely cause: CSV import created phantom posts with broken IDs
- Fix: `python cleanup_duplicates.py` then re-export
- Prevention: CSV importer now only UPDATES, never INSERTS

### "Views/reach showing 0"
- CSV hasn't been imported, or CSV date range doesn't cover those posts
- Export fresh CSV from Meta Business Suite, put in `exports/from content manual Export/`
- Run `python import_manual_exports.py`

### "Token expired"
- Page tokens expire every 60 days
- Run `python get_page_tokens.py` to refresh
- Update `page_tokens.json`

### "Duplicate posts"
- Run `python cleanup_duplicates.py`
- Check for posts with IDs ending in `0000000` (precision loss): should be 0

## Key Metrics
- **PES** = Reactions×1 + Comments×2 + Shares×3
- **QES** = (Love+Wow+Haha) / Total Reactions × 100
- **Engagement** = Reactions + Comments + Shares
