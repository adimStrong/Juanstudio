"""
Ligaya vs JuanBabes Comparison Report Generator
Queries both JuanStudio and JuanBabes databases, generates a single HTML report.
"""
import sqlite3
import os
from datetime import datetime

JUANSTUDIO_DB = r"C:\Users\us\Desktop\juanstudio_project\data\juanstudio_analytics.db"
JUANBABES_DB = r"C:\Users\us\Desktop\juanbabes_project\data\juanbabes_analytics.db"
OUTPUT_HTML = r"C:\Users\us\Desktop\juanstudio_project\reports\ligaya_vs_juanbabes_comparison.html"

def query_db(db_path, sql, params=()):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(sql, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows

def fmt(n):
    """Format number with commas"""
    if n is None: return "0"
    if isinstance(n, float): return f"{n:,.1f}"
    return f"{int(n):,}"

def pct(n):
    if n is None: return "0.0%"
    return f"{n:.2f}%"

# ── 1. Overall stats per page ──────────────────────────────────────────────
def get_overall_stats():
    pages = []
    # Ligaya from JuanStudio
    rows = query_db(JUANSTUDIO_DB, """
        SELECT p2.page_name,
               COUNT(*) as posts,
               COALESCE(SUM(p.views_count),0) as views,
               COALESCE(SUM(p.reach_count),0) as reach,
               COALESCE(SUM(p.reactions_total),0) as reactions,
               COALESCE(SUM(p.comments_count),0) as comments,
               COALESCE(SUM(p.shares_count),0) as shares,
               COALESCE(SUM(p.total_engagement),0) as engagement,
               COALESCE(AVG(p.pes),0) as avg_pes,
               COALESCE(SUM(p.pes),0) as total_pes
        FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
        WHERE p2.page_name = 'Juankada Ligaya'
        GROUP BY p2.page_name
    """)
    for r in rows:
        r['source'] = 'juankada'
        pages.append(r)

    # All 5 JuanBabes
    rows = query_db(JUANBABES_DB, """
        SELECT p2.page_name,
               COUNT(*) as posts,
               COALESCE(SUM(p.views_count),0) as views,
               COALESCE(SUM(p.reach_count),0) as reach,
               COALESCE(SUM(p.reactions_total),0) as reactions,
               COALESCE(SUM(p.comments_count),0) as comments,
               COALESCE(SUM(p.shares_count),0) as shares,
               COALESCE(SUM(p.total_engagement),0) as engagement,
               COALESCE(AVG(p.pes),0) as avg_pes,
               COALESCE(SUM(p.pes),0) as total_pes
        FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
        GROUP BY p2.page_name
        ORDER BY SUM(p.views_count) DESC
    """)
    for r in rows:
        r['source'] = 'juanbabes'
        pages.append(r)
    return pages

# ── 2. February 2026 stats ─────────────────────────────────────────────────
def get_feb_stats():
    pages = []
    # Ligaya Feb
    rows = query_db(JUANSTUDIO_DB, """
        SELECT p2.page_name,
               COUNT(*) as posts,
               COALESCE(SUM(p.views_count),0) as views,
               COALESCE(SUM(p.reach_count),0) as reach,
               COALESCE(SUM(p.reactions_total),0) as reactions,
               COALESCE(SUM(p.comments_count),0) as comments,
               COALESCE(SUM(p.shares_count),0) as shares,
               COALESCE(SUM(p.total_engagement),0) as engagement,
               COALESCE(AVG(p.pes),0) as avg_pes
        FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
        WHERE p2.page_name = 'Juankada Ligaya'
          AND p.publish_time >= '2026-02-01' AND p.publish_time < '2026-03-01'
        GROUP BY p2.page_name
    """)
    for r in rows:
        r['source'] = 'juankada'
        pages.append(r)

    rows = query_db(JUANBABES_DB, """
        SELECT p2.page_name,
               COUNT(*) as posts,
               COALESCE(SUM(p.views_count),0) as views,
               COALESCE(SUM(p.reach_count),0) as reach,
               COALESCE(SUM(p.reactions_total),0) as reactions,
               COALESCE(SUM(p.comments_count),0) as comments,
               COALESCE(SUM(p.shares_count),0) as shares,
               COALESCE(SUM(p.total_engagement),0) as engagement,
               COALESCE(AVG(p.pes),0) as avg_pes
        FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
        WHERE p.publish_time >= '2026-02-01' AND p.publish_time < '2026-03-01'
        GROUP BY p2.page_name
        ORDER BY SUM(p.views_count) DESC
    """)
    for r in rows:
        r['source'] = 'juanbabes'
        pages.append(r)
    return pages

# ── 3. Monthly trend (Dec 2025 - Feb 2026) ─────────────────────────────────
def get_monthly_trend():
    trend = {}
    for db, page_filter, label in [
        (JUANSTUDIO_DB, "p2.page_name = 'Juankada Ligaya'", "Ligaya"),
        (JUANBABES_DB, "p2.page_name = 'Juana Babe Ashley'", "Ashley"),
        (JUANBABES_DB, "p2.page_name = 'Juana Babe Sena'", "Sena"),
    ]:
        rows = query_db(db, f"""
            SELECT substr(p.publish_time, 1, 7) as month,
                   COUNT(*) as posts,
                   COALESCE(SUM(p.views_count),0) as views,
                   COALESCE(SUM(p.reactions_total),0) as reactions,
                   COALESCE(AVG(p.pes),0) as avg_pes
            FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
            WHERE {page_filter}
              AND p.publish_time >= '2025-12-01' AND p.publish_time < '2026-03-01'
            GROUP BY substr(p.publish_time, 1, 7)
            ORDER BY month
        """)
        trend[label] = rows
    return trend

# ── 4. Content type distribution ────────────────────────────────────────────
def get_content_types():
    types = {}
    for db, page_filter, label in [
        (JUANSTUDIO_DB, "p2.page_name = 'Juankada Ligaya'", "Ligaya"),
        (JUANBABES_DB, "p2.page_name = 'Juana Babe Ashley'", "Ashley"),
        (JUANBABES_DB, "p2.page_name = 'Juana Babe Sena'", "Sena"),
        (JUANBABES_DB, "p2.page_name = 'Juana Babe Abi'", "Abi"),
        (JUANBABES_DB, "p2.page_name = 'Juana Babe Jam'", "Jam"),
        (JUANBABES_DB, "p2.page_name = 'Juana Babe Zell'", "Zell"),
    ]:
        rows = query_db(db, f"""
            SELECT p.post_type,
                   COUNT(*) as cnt,
                   COALESCE(AVG(p.views_count),0) as avg_views,
                   COALESCE(AVG(p.pes),0) as avg_pes
            FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
            WHERE {page_filter}
            GROUP BY p.post_type
            ORDER BY cnt DESC
        """)
        types[label] = rows
    return types

# ── 5. Top posts ────────────────────────────────────────────────────────────
def get_top_posts(feb_only=False):
    date_filter = "AND p.publish_time >= '2026-02-01' AND p.publish_time < '2026-03-01'" if feb_only else ""
    top = {}
    for db, page_filter, label in [
        (JUANSTUDIO_DB, "p2.page_name = 'Juankada Ligaya'", "Ligaya"),
        (JUANBABES_DB, "p2.page_name = 'Juana Babe Ashley'", "Ashley"),
        (JUANBABES_DB, "p2.page_name = 'Juana Babe Sena'", "Sena"),
    ]:
        rows = query_db(db, f"""
            SELECT p2.page_name, p.post_type, p.publish_time,
                   COALESCE(p.title, p.description, '') as caption,
                   p.views_count, p.reactions_total, p.comments_count,
                   p.shares_count, p.total_engagement, p.pes, p.permalink
            FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
            WHERE {page_filter} {date_filter}
            ORDER BY p.pes DESC
            LIMIT 5
        """)
        top[label] = rows
    return top


# ── HTML Generation ─────────────────────────────────────────────────────────
def short_name(page_name):
    return page_name.replace("Juankada ", "").replace("Juana Babe ", "")

def generate_html():
    overall = get_overall_stats()
    feb = get_feb_stats()
    trend = get_monthly_trend()
    ctypes = get_content_types()
    top_overall = get_top_posts(feb_only=False)
    top_feb = get_top_posts(feb_only=True)

    # Sort overall by avg views/post desc
    overall.sort(key=lambda x: x['views'] / max(x['posts'], 1), reverse=True)
    feb.sort(key=lambda x: x['views'] / max(x['posts'], 1), reverse=True)

    # Hero cards: Ligaya, Ashley, Sena
    heroes = []
    for name in ['Juankada Ligaya', 'Juana Babe Ashley', 'Juana Babe Sena']:
        for p in overall:
            if p['page_name'] == name:
                heroes.append(p)
                break

    # Calculate comparison ratios
    ligaya = heroes[0] if heroes else {}
    ashley = heroes[1] if len(heroes) > 1 else {}
    ligaya_avg_views = ligaya['views'] / max(ligaya['posts'], 1) if ligaya else 0
    ashley_avg_views = ashley['views'] / max(ashley['posts'], 1) if ashley else 1
    views_ratio = ligaya_avg_views / ashley_avg_views if ashley_avg_views else 0

    ligaya_eng_rate = (ligaya['reactions'] / max(ligaya['reach'], 1) * 100) if ligaya else 0
    ashley_eng_rate = (ashley['reactions'] / max(ashley['reach'], 1) * 100) if ashley else 0
    eng_ratio = ligaya_eng_rate / ashley_eng_rate if ashley_eng_rate else 0

    now = datetime.now().strftime("%B %d, %Y")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ligaya vs JuanBabes - Comparison Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1100px; margin: 0 auto; }}

        header {{
            text-align: center;
            padding: 40px 20px;
            background: linear-gradient(135deg, #f5576c 0%, #f093fb 50%, #7b2cbf 100%);
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(245, 87, 108, 0.3);
        }}
        header h1 {{ font-size: 2.2rem; margin-bottom: 8px; }}
        header .subtitle {{ font-size: 1.3rem; opacity: 0.95; font-weight: 300; }}
        .report-date {{
            background: rgba(255,255,255,0.2);
            padding: 8px 20px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 15px;
            font-weight: 600;
        }}

        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .section h2 {{
            color: #f5576c;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(245, 87, 108, 0.3);
            font-size: 1.4rem;
        }}
        .section h3 {{
            color: #f093fb;
            margin: 20px 0 12px;
            font-size: 1.1rem;
        }}

        /* Hero cards */
        .hero-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }}
        .hero-card {{
            background: rgba(255,255,255,0.08);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            border: 2px solid rgba(255,255,255,0.1);
            transition: transform 0.2s;
        }}
        .hero-card:first-child {{
            border-color: #f5576c;
            box-shadow: 0 0 20px rgba(245, 87, 108, 0.2);
        }}
        .hero-card .name {{ font-size: 1.3rem; font-weight: 700; margin-bottom: 5px; }}
        .hero-card .brand {{ font-size: 0.8rem; opacity: 0.6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px; }}
        .hero-card .stat {{ margin: 8px 0; }}
        .hero-card .stat .value {{ font-size: 1.5rem; font-weight: 700; color: #f5576c; }}
        .hero-card .stat .label {{ font-size: 0.75rem; opacity: 0.6; text-transform: uppercase; }}

        .insight-box {{
            background: linear-gradient(135deg, rgba(245, 87, 108, 0.15), rgba(240, 147, 251, 0.1));
            border: 1px solid rgba(245, 87, 108, 0.3);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            margin: 20px 0;
        }}
        .insight-box .headline {{
            font-size: 1.3rem;
            font-weight: 700;
            color: #f5576c;
        }}
        .insight-box .detail {{ opacity: 0.8; margin-top: 5px; }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 0.9rem;
        }}
        th, td {{
            padding: 12px 10px;
            text-align: right;
            border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        th {{
            background: rgba(245, 87, 108, 0.15);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.7rem;
            letter-spacing: 0.5px;
            color: #f093fb;
        }}
        th:first-child, td:first-child {{ text-align: left; }}
        tr:hover {{ background: rgba(255,255,255,0.03); }}
        .highlight-row {{ background: rgba(245, 87, 108, 0.08) !important; font-weight: 600; }}
        .winner {{ color: #4ade80; font-weight: 700; }}
        .best-cell {{ color: #4ade80; }}
        .brand-tag {{
            font-size: 0.65rem;
            padding: 2px 6px;
            border-radius: 4px;
            margin-left: 6px;
            font-weight: 600;
        }}
        .tag-juankada {{ background: rgba(245, 87, 108, 0.3); color: #f5576c; }}
        .tag-juanbabes {{ background: rgba(123, 44, 191, 0.3); color: #c084fc; }}

        /* Trend table */
        .trend-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }}
        .trend-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            padding: 15px;
        }}
        .trend-card .page-name {{ font-weight: 700; margin-bottom: 10px; color: #f5576c; }}

        /* Top posts */
        .top-posts-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }}
        .top-post-col h4 {{
            color: #f093fb;
            margin-bottom: 10px;
            font-size: 1rem;
        }}
        .post-card {{
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 10px;
            border-left: 3px solid rgba(245, 87, 108, 0.4);
        }}
        .post-card .post-rank {{ color: #f5576c; font-weight: 700; font-size: 0.8rem; }}
        .post-card .post-caption {{
            font-size: 0.8rem;
            opacity: 0.7;
            margin: 5px 0;
            overflow: hidden;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }}
        .post-card .post-stats {{ font-size: 0.75rem; opacity: 0.8; }}
        .post-card .post-stats span {{ margin-right: 10px; }}
        .post-card .post-pes {{ color: #f5576c; font-weight: 700; }}
        .post-card a {{ color: #7dd3fc; text-decoration: none; font-size: 0.75rem; }}
        .post-card a:hover {{ text-decoration: underline; }}

        /* Content type bars */
        .ctype-bar {{
            display: flex;
            height: 28px;
            border-radius: 6px;
            overflow: hidden;
            margin: 8px 0;
        }}
        .ctype-bar div {{
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7rem;
            font-weight: 600;
        }}
        .ct-video {{ background: #f5576c; }}
        .ct-photos {{ background: #7b2cbf; }}
        .ct-reel {{ background: #3b82f6; }}
        .ct-other {{ background: rgba(255,255,255,0.15); }}

        .ctype-legend {{
            display: flex;
            gap: 15px;
            margin: 10px 0;
            font-size: 0.8rem;
        }}
        .ctype-legend span::before {{
            content: '';
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 3px;
            margin-right: 5px;
            vertical-align: middle;
        }}
        .ctype-legend .l-video::before {{ background: #f5576c; }}
        .ctype-legend .l-photos::before {{ background: #7b2cbf; }}
        .ctype-legend .l-reel::before {{ background: #3b82f6; }}
        .ctype-legend .l-other::before {{ background: rgba(255,255,255,0.15); }}

        .footer {{
            text-align: center;
            padding: 20px;
            opacity: 0.4;
            font-size: 0.8rem;
        }}
        @media (max-width: 768px) {{
            .hero-grid, .trend-grid, .top-posts-grid {{ grid-template-columns: 1fr; }}
            table {{ font-size: 0.8rem; }}
            th, td {{ padding: 8px 6px; }}
        }}
    </style>
</head>
<body>
<div class="container">

<header>
    <h1>Ligaya vs JuanBabes</h1>
    <div class="subtitle">Cross-Brand Performance Comparison</div>
    <div class="report-date">Generated {now}</div>
</header>
"""

    # ── Section 1: Executive Summary ──
    html += '<div class="section"><h2>Executive Summary</h2>\n'
    html += '<div class="hero-grid">\n'
    for i, h in enumerate(heroes):
        sn = short_name(h['page_name'])
        brand = "Juankada" if h['source'] == 'juankada' else "JuanBabes"
        tag_cls = "tag-juankada" if h['source'] == 'juankada' else "tag-juanbabes"
        avg_v = h['views'] / max(h['posts'], 1)
        eng_r = h['reactions'] / max(h['reach'], 1) * 100
        html += f'''<div class="hero-card">
    <div class="name">{sn}</div>
    <div class="brand"><span class="brand-tag {tag_cls}">{brand}</span></div>
    <div class="stat"><div class="value">{fmt(h["posts"])}</div><div class="label">Total Posts</div></div>
    <div class="stat"><div class="value">{fmt(h["views"])}</div><div class="label">Total Views</div></div>
    <div class="stat"><div class="value">{fmt(avg_v)}</div><div class="label">Avg Views/Post</div></div>
    <div class="stat"><div class="value">{pct(eng_r)}</div><div class="label">Engagement Rate</div></div>
    <div class="stat"><div class="value">{fmt(h["avg_pes"])}</div><div class="label">Avg PES</div></div>
</div>\n'''
    html += '</div>\n'

    html += f'''<div class="insight-box">
    <div class="headline">Ligaya gets {views_ratio:.1f}x more views per post than Ashley</div>
    <div class="detail">With only {fmt(ligaya["posts"])} posts vs Ashley's {fmt(ashley["posts"])}, Ligaya's engagement rate ({pct(ligaya_eng_rate)}) is {eng_ratio:.1f}x higher</div>
</div>\n'''

    # ── Improvement #1: Killer stat — Ligaya vs ALL JuanBabes combined ──
    jb_total = query_db(JUANBABES_DB, "SELECT COUNT(*) as posts, COALESCE(SUM(views_count),0) as views, COALESCE(SUM(reactions_total),0) as reactions FROM posts")
    if jb_total:
        jb = jb_total[0]
        vol_pct = ligaya['posts'] / max(jb['posts'], 1) * 100
        views_pct = ligaya['views'] / max(jb['views'], 1) * 100
        html += f'''<div style="background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%); color: #1a1a2e; padding: 25px; border-radius: 12px; text-align: center; margin: 20px 0;">
    <div style="font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; opacity: 0.8;">The Headline Number</div>
    <div style="font-size: 2.5rem; font-weight: 800; margin: 10px 0;">{vol_pct:.1f}% of the posts, {views_pct:.1f}% of the views</div>
    <div style="font-size: 1.05rem;">Ligaya's {fmt(ligaya["posts"])} posts generate <strong>half the total views</strong> of all 5 JuanBabes pages combined ({fmt(jb["posts"])} posts)</div>
</div>\n'''

    html += '</div>\n'

    # ── Section 2: Overall Comparison Table ──
    html += '<div class="section"><h2>Overall Comparison (All Time)</h2>\n'
    html += '<h3>Totals</h3>\n'
    html += '<table><thead><tr>'
    html += '<th>Page</th><th>Posts</th><th>Views</th><th>Reach</th><th>Reactions</th><th>Comments</th><th>Shares</th><th>Eng Rate</th><th>Avg PES</th>'
    html += '</tr></thead><tbody>\n'

    # Find best in each column for highlighting
    metrics_keys = ['posts', 'views', 'reach', 'reactions', 'comments', 'shares']
    best = {}
    for k in metrics_keys:
        best[k] = max(overall, key=lambda x: x[k])['page_name']
    best['eng_rate'] = max(overall, key=lambda x: x['reactions']/max(x['reach'],1))['page_name']
    best['avg_pes'] = max(overall, key=lambda x: x['avg_pes'])['page_name']

    for p in overall:
        sn = short_name(p['page_name'])
        brand = "Juankada" if p['source'] == 'juankada' else "JuanBabes"
        tag_cls = "tag-juankada" if p['source'] == 'juankada' else "tag-juanbabes"
        eng_r = p['reactions'] / max(p['reach'], 1) * 100
        row_cls = ' class="highlight-row"' if p['page_name'] == 'Juankada Ligaya' else ''

        def cell(key, val):
            cls = ' class="best-cell"' if best.get(key) == p['page_name'] else ''
            return f'<td{cls}>{val}</td>'

        html += f'<tr{row_cls}>'
        html += f'<td>{sn} <span class="brand-tag {tag_cls}">{brand}</span></td>'
        html += cell('posts', fmt(p['posts']))
        html += cell('views', fmt(p['views']))
        html += cell('reach', fmt(p['reach']))
        html += cell('reactions', fmt(p['reactions']))
        html += cell('comments', fmt(p['comments']))
        html += cell('shares', fmt(p['shares']))
        html += cell('eng_rate', pct(eng_r))
        html += cell('avg_pes', fmt(p['avg_pes']))
        html += '</tr>\n'
    html += '</tbody></table>\n'

    # Per-post averages
    html += '<h3>Per-Post Averages</h3>\n'
    html += '<table><thead><tr>'
    html += '<th>Page</th><th>Avg Views</th><th>Avg Reach</th><th>Avg Reactions</th><th>Avg Comments</th><th>Avg Shares</th><th>Avg Engagement</th><th>Avg PES</th>'
    html += '</tr></thead><tbody>\n'

    avg_best = {}
    for k in ['views', 'reach', 'reactions', 'comments', 'shares', 'engagement']:
        avg_best[k] = max(overall, key=lambda x: x[k]/max(x['posts'],1))['page_name']
    avg_best['avg_pes'] = max(overall, key=lambda x: x['avg_pes'])['page_name']

    for p in overall:
        sn = short_name(p['page_name'])
        brand = "Juankada" if p['source'] == 'juankada' else "JuanBabes"
        tag_cls = "tag-juankada" if p['source'] == 'juankada' else "tag-juanbabes"
        n = max(p['posts'], 1)
        row_cls = ' class="highlight-row"' if p['page_name'] == 'Juankada Ligaya' else ''

        def cell2(key, val):
            cls = ' class="best-cell"' if avg_best.get(key) == p['page_name'] else ''
            return f'<td{cls}>{val}</td>'

        html += f'<tr{row_cls}>'
        html += f'<td>{sn} <span class="brand-tag {tag_cls}">{brand}</span></td>'
        html += cell2('views', fmt(p['views']/n))
        html += cell2('reach', fmt(p['reach']/n))
        html += cell2('reactions', fmt(p['reactions']/n))
        html += cell2('comments', fmt(p['comments']/n))
        html += cell2('shares', fmt(p['shares']/n))
        html += cell2('engagement', fmt(p['engagement']/n))
        html += cell2('avg_pes', fmt(p['avg_pes']))
        html += '</tr>\n'
    html += '</tbody></table>\n'
    html += '</div>\n'

    # ── Section 3: February 2026 Comparison ──
    html += '<div class="section"><h2>February 2026 Comparison (Feb 1-14)</h2>\n'

    if feb:
        # Find Feb winner
        feb_winner = max(feb, key=lambda x: x['views']/max(x['posts'],1))
        feb_winner_name = short_name(feb_winner['page_name'])
        feb_winner_avg = feb_winner['views'] / max(feb_winner['posts'], 1)
        html += f'<div class="insight-box"><div class="headline">{feb_winner_name} leads February with {fmt(feb_winner_avg)} avg views/post ({fmt(feb_winner["posts"])} posts)</div></div>\n'

        html += '<table><thead><tr>'
        html += '<th>Page</th><th>Posts</th><th>Views</th><th>Reach</th><th>Reactions</th><th>Comments</th><th>Shares</th><th>Eng Rate</th><th>Avg PES</th>'
        html += '</tr></thead><tbody>\n'

        for p in feb:
            sn = short_name(p['page_name'])
            brand = "Juankada" if p['source'] == 'juankada' else "JuanBabes"
            tag_cls = "tag-juankada" if p['source'] == 'juankada' else "tag-juanbabes"
            eng_r = p['reactions'] / max(p['reach'], 1) * 100
            row_cls = ' class="highlight-row"' if p['page_name'] == 'Juankada Ligaya' else ''
            html += f'<tr{row_cls}>'
            html += f'<td>{sn} <span class="brand-tag {tag_cls}">{brand}</span></td>'
            html += f'<td>{fmt(p["posts"])}</td><td>{fmt(p["views"])}</td><td>{fmt(p["reach"])}</td>'
            html += f'<td>{fmt(p["reactions"])}</td><td>{fmt(p["comments"])}</td><td>{fmt(p["shares"])}</td>'
            html += f'<td>{pct(eng_r)}</td><td>{fmt(p["avg_pes"])}</td>'
            html += '</tr>\n'
        html += '</tbody></table>\n'

        # Per-post averages for Feb
        html += '<h3>February Per-Post Averages</h3>\n'
        html += '<table><thead><tr>'
        html += '<th>Page</th><th>Posts</th><th>Avg Views</th><th>Avg Reach</th><th>Avg Reactions</th><th>Avg Comments</th><th>Avg Shares</th><th>Avg PES</th>'
        html += '</tr></thead><tbody>\n'
        for p in feb:
            sn = short_name(p['page_name'])
            brand = "Juankada" if p['source'] == 'juankada' else "JuanBabes"
            tag_cls = "tag-juankada" if p['source'] == 'juankada' else "tag-juanbabes"
            n = max(p['posts'], 1)
            row_cls = ' class="highlight-row"' if p['page_name'] == 'Juankada Ligaya' else ''
            html += f'<tr{row_cls}>'
            html += f'<td>{sn} <span class="brand-tag {tag_cls}">{brand}</span></td>'
            html += f'<td>{fmt(p["posts"])}</td><td>{fmt(p["views"]/n)}</td><td>{fmt(p["reach"]/n)}</td>'
            html += f'<td>{fmt(p["reactions"]/n)}</td><td>{fmt(p["comments"]/n)}</td><td>{fmt(p["shares"]/n)}</td>'
            html += f'<td>{fmt(p["avg_pes"])}</td>'
            html += '</tr>\n'
        html += '</tbody></table>\n'
    else:
        html += '<p>No February 2026 data available.</p>\n'

    html += '</div>\n'

    # ── Section 4: Monthly Trend ──
    html += '<div class="section"><h2>Monthly Trend (Dec 2025 - Feb 2026)</h2>\n'

    # ── Improvement #2: Trajectory insight box ──
    # Calculate Dec→Feb changes for each page
    trajectory_parts = []
    for label in ['Ligaya', 'Ashley', 'Sena']:
        months = trend.get(label, [])
        month_map = {r['month']: r for r in months}
        dec = month_map.get('2025-12')
        feb = month_map.get('2026-02')
        if dec and feb and dec['views'] > 0:
            change_pct = (feb['views'] - dec['views']) / dec['views'] * 100
            trajectory_parts.append((label, dec['views'], feb['views'], change_pct))

    if trajectory_parts:
        html += '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-bottom:20px;">\n'
        for label, dec_v, feb_v, change in trajectory_parts:
            if change > 0:
                arrow = '&#9650;'  # up
                color = '#4ade80'
                sign = '+'
            else:
                arrow = '&#9660;'  # down
                color = '#f87171'
                sign = ''
            html += f'''<div style="background:rgba(255,255,255,0.06);border-radius:10px;padding:18px;text-align:center;border-top:3px solid {color};">
    <div style="font-weight:700;font-size:1.1rem;margin-bottom:8px;">{label}</div>
    <div style="font-size:2rem;font-weight:800;color:{color};">{arrow} {sign}{change:,.0f}%</div>
    <div style="font-size:0.8rem;opacity:0.6;">Dec: {fmt(dec_v)} views</div>
    <div style="font-size:0.8rem;opacity:0.6;">Feb: {fmt(feb_v)} views</div>
</div>\n'''
        html += '</div>\n'

        # Narrative insight
        lig_t = next((t for t in trajectory_parts if t[0] == 'Ligaya'), None)
        ash_t = next((t for t in trajectory_parts if t[0] == 'Ashley'), None)
        if lig_t and ash_t:
            html += f'''<div class="insight-box">
    <div class="headline">Opposite trajectories: Ligaya is surging, JuanBabes is fading</div>
    <div class="detail">Since December, Ligaya's monthly views grew {lig_t[3]:+,.0f}% while Ashley dropped {ash_t[3]:,.0f}%. Ligaya is accelerating — averaging {fmt(lig_t[2])} views in Feb (half-month) vs {fmt(lig_t[1])} for all of December.</div>
</div>\n'''

    html += '<div class="trend-grid">\n'

    month_labels = {'2025-12': 'Dec 2025', '2026-01': 'Jan 2026', '2026-02': 'Feb 2026'}
    for label in ['Ligaya', 'Ashley', 'Sena']:
        html += f'<div class="trend-card"><div class="page-name">{label}</div>\n'
        html += '<table><thead><tr><th>Month</th><th>Posts</th><th>Views</th><th>Reactions</th><th>Avg PES</th></tr></thead><tbody>\n'
        for row in trend.get(label, []):
            ml = month_labels.get(row['month'], row['month'])
            html += f'<tr><td>{ml}</td><td>{fmt(row["posts"])}</td><td>{fmt(row["views"])}</td><td>{fmt(row["reactions"])}</td><td>{fmt(row["avg_pes"])}</td></tr>\n'
        html += '</tbody></table></div>\n'
    html += '</div></div>\n'

    # ── Section 5: Content Strategy ──
    html += '<div class="section"><h2>Content Strategy</h2>\n'
    html += '<div class="ctype-legend"><span class="l-video">Video/Live</span><span class="l-reel">Reel</span><span class="l-photos">Photos</span><span class="l-other">Other</span></div>\n'

    for label in ['Ligaya', 'Ashley', 'Sena', 'Abi', 'Jam', 'Zell']:
        rows = ctypes.get(label, [])
        if not rows:
            continue
        total = sum(r['cnt'] for r in rows)
        type_map = {}
        for r in rows:
            pt = (r['post_type'] or '').lower()
            if 'video' in pt or 'live' in pt:
                type_map.setdefault('video', {'cnt': 0, 'avg_views': 0})
                type_map['video']['cnt'] += r['cnt']
                type_map['video']['avg_views'] = r['avg_views']
            elif 'reel' in pt:
                type_map.setdefault('reel', {'cnt': 0, 'avg_views': 0})
                type_map['reel']['cnt'] += r['cnt']
                type_map['reel']['avg_views'] = r['avg_views']
            elif 'photo' in pt:
                type_map.setdefault('photos', {'cnt': 0, 'avg_views': 0})
                type_map['photos']['cnt'] += r['cnt']
                type_map['photos']['avg_views'] = r['avg_views']
            else:
                type_map.setdefault('other', {'cnt': 0, 'avg_views': 0})
                type_map['other']['cnt'] += r['cnt']
                type_map['other']['avg_views'] = r['avg_views']

        html += f'<div style="margin: 12px 0;"><strong>{label}</strong> ({total} posts)\n'
        html += '<div class="ctype-bar">'
        for ct, cls in [('video', 'ct-video'), ('reel', 'ct-reel'), ('photos', 'ct-photos'), ('other', 'ct-other')]:
            if ct in type_map:
                w = type_map[ct]['cnt'] / total * 100
                if w > 5:
                    html += f'<div class="{cls}" style="width:{w:.1f}%">{type_map[ct]["cnt"]} ({w:.0f}%)</div>'
                elif w > 0:
                    html += f'<div class="{cls}" style="width:{w:.1f}%"></div>'
        html += '</div>\n'

        # Show avg views by type
        parts = []
        for ct, clabel in [('video', 'Video/Live'), ('reel', 'Reel'), ('photos', 'Photos')]:
            if ct in type_map and type_map[ct]['cnt'] > 0:
                parts.append(f'{clabel}: {fmt(type_map[ct]["avg_views"])} avg views')
        if parts:
            html += f'<div style="font-size:0.75rem;opacity:0.6;margin-top:3px">{" | ".join(parts)}</div>\n'
        html += '</div>\n'

    html += '</div>\n'

    # ── Section 6: Top 5 Posts ──
    for section_label, top_data in [("Top 5 Posts (Overall)", top_overall), ("Top 5 Posts (February 2026)", top_feb)]:
        html += f'<div class="section"><h2>{section_label}</h2>\n'
        html += '<div class="top-posts-grid">\n'
        for label in ['Ligaya', 'Ashley', 'Sena']:
            html += f'<div class="top-post-col"><h4>{label}</h4>\n'
            posts = top_data.get(label, [])
            for i, post in enumerate(posts):
                caption = (post['caption'] or '')[:100]
                if len(post['caption'] or '') > 100:
                    caption += '...'
                date = post['publish_time'][:10] if post['publish_time'] else ''
                link = post.get('permalink', '')
                html += f'''<div class="post-card">
    <div class="post-rank">#{i+1} &middot; {post["post_type"] or "Post"} &middot; {date}</div>
    <div class="post-caption">{caption}</div>
    <div class="post-stats">
        <span>&#128064; {fmt(post["views_count"])}</span>
        <span>&#10084; {fmt(post["reactions_total"])}</span>
        <span>&#128172; {fmt(post["comments_count"])}</span>
        <span>&#128257; {fmt(post["shares_count"])}</span>
        <span class="post-pes">PES {fmt(post["pes"])}</span>
    </div>
    {"<a href='" + link + "' target='_blank'>View Post</a>" if link else ""}
</div>\n'''
            if not posts:
                html += '<p style="opacity:0.5;font-size:0.85rem">No posts in this period</p>\n'
            html += '</div>\n'
        html += '</div></div>\n'

    # ── Section 7: Recommendations ──
    # Get Ligaya video stats vs Ashley stats for data-driven recs
    lig_video = query_db(JUANSTUDIO_DB, """
        SELECT COUNT(*) as cnt, AVG(views_count) as avg_v, AVG(pes) as avg_pes
        FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
        WHERE p2.page_name = 'Juankada Ligaya' AND LOWER(p.post_type) LIKE '%video%'
    """)
    lig_photo = query_db(JUANSTUDIO_DB, """
        SELECT COUNT(*) as cnt, AVG(views_count) as avg_v, AVG(pes) as avg_pes
        FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
        WHERE p2.page_name = 'Juankada Ligaya' AND LOWER(p.post_type) LIKE '%photo%'
    """)
    ash_reel = query_db(JUANBABES_DB, """
        SELECT COUNT(*) as cnt, AVG(views_count) as avg_v, AVG(pes) as avg_pes
        FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
        WHERE p2.page_name = 'Juana Babe Ashley' AND LOWER(p.post_type) LIKE '%reel%'
    """)
    ash_video = query_db(JUANBABES_DB, """
        SELECT COUNT(*) as cnt, AVG(views_count) as avg_v, AVG(pes) as avg_pes
        FROM posts p JOIN pages p2 ON p.page_id = p2.page_id
        WHERE p2.page_name = 'Juana Babe Ashley' AND LOWER(p.post_type) LIKE '%video%'
    """)

    lv = lig_video[0] if lig_video else {}
    lp = lig_photo[0] if lig_photo else {}
    ar = ash_reel[0] if ash_reel else {}
    av = ash_video[0] if ash_video else {}

    video_vs_photo = (lv.get('avg_v',0) or 0) / max(lp.get('avg_v',1) or 1, 1)

    html += '<div class="section"><h2>Recommendations: What JuanBabes Can Learn from Ligaya</h2>\n'

    html += '''<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:20px;margin-bottom:20px;">\n'''

    # Rec 1: Video-first strategy
    html += f'''<div style="background:rgba(245,87,108,0.08);border-radius:12px;padding:20px;border-left:4px solid #f5576c;">
    <div style="font-weight:700;font-size:1.1rem;color:#f5576c;margin-bottom:8px;">1. Go Video-First</div>
    <div style="font-size:0.9rem;opacity:0.9;">Ligaya's Videos average <strong>{fmt(lv.get("avg_v",0))} views</strong> vs Photos at {fmt(lp.get("avg_v",0))} ({video_vs_photo:.0f}x difference). {fmt(lv.get("cnt",0))} of her {fmt(ligaya["posts"])} posts are Videos — that's {lv.get("cnt",0)/max(ligaya["posts"],1)*100:.0f}% video content.</div>
    <div style="font-size:0.8rem;color:#f093fb;margin-top:8px;">Ashley's Reels ({fmt(ar.get("cnt",0))}) avg {fmt(ar.get("avg_v",0))} views — her best format. But her Videos ({fmt(av.get("cnt",0))}) only avg {fmt(av.get("avg_v",0))}. Consider shifting Videos to Reels or studying Ligaya's Video format.</div>
</div>\n'''

    # Rec 2: Quality over quantity
    html += f'''<div style="background:rgba(74,222,128,0.08);border-radius:12px;padding:20px;border-left:4px solid #4ade80;">
    <div style="font-weight:700;font-size:1.1rem;color:#4ade80;margin-bottom:8px;">2. Quality Over Quantity</div>
    <div style="font-size:0.9rem;opacity:0.9;">Ligaya posts <strong>{ligaya["posts"]/3:.0f}x/month</strong> avg. Ashley posts <strong>{ashley["posts"]/5:.0f}x/month</strong> avg. Yet Ligaya's per-post engagement is {eng_ratio:.1f}x higher.</div>
    <div style="font-size:0.8rem;color:#f093fb;margin-top:8px;">More posts ≠ more reach. JuanBabes pages should test reducing posting frequency by 30-40% and investing more production value per post.</div>
</div>\n'''

    # Rec 3: Engagement rate
    html += f'''<div style="background:rgba(123,44,191,0.08);border-radius:12px;padding:20px;border-left:4px solid #7b2cbf;">
    <div style="font-weight:700;font-size:1.1rem;color:#c084fc;margin-bottom:8px;">3. Drive Engagement, Not Just Views</div>
    <div style="font-size:0.9rem;opacity:0.9;">Ligaya's engagement rate is <strong>{pct(ligaya_eng_rate)}</strong> — meaning {ligaya_eng_rate:.0f} out of 100 people who see her content react. Ashley's is {pct(ashley_eng_rate)}.</div>
    <div style="font-size:0.8rem;color:#f093fb;margin-top:8px;">High engagement signals the algorithm to push content further. Ligaya's audience is deeply engaged — not passive scrollers. JuanBabes should focus on CTA hooks and community-building content.</div>
</div>\n'''

    # Rec 4: Trajectory warning
    html += f'''<div style="background:rgba(248,113,113,0.08);border-radius:12px;padding:20px;border-left:4px solid #f87171;">
    <div style="font-weight:700;font-size:1.1rem;color:#f87171;margin-bottom:8px;">4. Address the Decline Now</div>
    <div style="font-size:0.9rem;opacity:0.9;">Ashley's views dropped from <strong>1.48M (Dec)</strong> to <strong>63K (Feb)</strong> — a <strong>95.7% decline</strong> in 2 months. Sena dropped 78.2%. This isn't seasonal — it's a content strategy problem.</div>
    <div style="font-size:0.8rem;color:#f093fb;margin-top:8px;">Meanwhile Ligaya went from 32K (Dec) to 1.1M (Feb) — a 3,310% increase. The gap is widening fast. Immediate A/B testing of content formats is recommended for JuanBabes.</div>
</div>\n'''

    html += '</div>\n'

    # Summary verdict
    html += f'''<div style="background: linear-gradient(135deg, rgba(245, 87, 108, 0.15), rgba(123, 44, 191, 0.15)); border: 2px solid rgba(245, 87, 108, 0.3); border-radius: 12px; padding: 25px; text-align: center;">
    <div style="font-size: 1.3rem; font-weight: 700; color: #f5576c; margin-bottom: 10px;">The Bottom Line</div>
    <div style="font-size: 1rem; opacity: 0.9;">Ligaya proves that <strong>one talent with the right content strategy</strong> can outperform an entire brand roster. JuanBabes has 5 pages and 17x more posts — but Ligaya alone captures half their total views. The playbook is clear: video-first, quality over quantity, and authentic engagement.</div>
</div>\n'''

    html += '</div>\n'

    html += f'''
<div class="footer">
    Ligaya vs JuanBabes Comparison Report &middot; Generated {now}<br>
    Data: JuanStudio Analytics DB + JuanBabes Analytics DB
</div>

</div>
</body>
</html>'''

    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Report generated: {OUTPUT_HTML}")
    print(f"File size: {os.path.getsize(OUTPUT_HTML):,} bytes")


if __name__ == '__main__':
    generate_html()
