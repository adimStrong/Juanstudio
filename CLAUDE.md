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

## Daily Morning Workflow

### When you have a NEW CSV from Meta:
```
1. Download CSV from Meta Business Suite (Content > Export)
2. Drop CSV into: exports\from content manual Export\
3. Double-click update_csv.bat    (imports views/reach from CSV)
4. Double-click update_api.bat    (fetches new posts + updates engagement for last 7 days)
5. Double-click push.bat          (cleanup + export + deploy to Vercel)
```

### When NO new CSV (just daily refresh):
```
1. Double-click update_api.bat    (fetches new posts + updates engagement for last 7 days)
2. Double-click push.bat          (cleanup + export + deploy to Vercel)
```

### IMPORTANT:
- **Views/reach ONLY come from CSV**, NOT from the API. If views show 0, you need a fresh CSV.
- **Meta CSV has 2-3 day lag** on views/reach data. Recent posts will show 0 until next CSV.
- **API gives**: new posts + reactions/comments/shares (updates last 7 days of existing posts)
- **CSV gives**: views, reach, reactions (overwrites with higher values only)
- Always run `update_api.bat` AFTER `update_csv.bat` (API engagement is more current)

### Bat files:
- `update_csv.bat` — imports CSV views/reach + exports JSON
- `update_api.bat` — fetches API posts + updates engagement + exports JSON
- `push.bat` — cleanup + export + git push + vercel deploy
- `daily.bat` — combines update_api + push (use when no new CSV)

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
