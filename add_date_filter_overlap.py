#!/usr/bin/env python3
"""Add DateFilter to Overlap.jsx and update api.js for JuanStudio"""
import os

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# 1. Update api.js - add dateRange to getPageComparison
api_file = os.path.join(PROJECT_DIR, 'frontend', 'src', 'services', 'api.js')
with open(api_file, 'r', encoding='utf-8') as f:
    api_content = f.read()

old_getPageComparison = '''export const getPageComparison = async () => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    return data.pageComparison || {
      pages: [],
      postTypesByPage: {},
      dominantTypes: {}
    };
  }
  return api.get('/stats/page-comparison/').then(res => res.data);
};'''

new_getPageComparison = '''export const getPageComparison = async (dateRange = {}) => {
  if (IS_PRODUCTION) {
    const data = await loadStaticData();
    const { startDate, endDate } = dateRange;

    // If no date filter, return cached comparison
    if (!startDate && !endDate) {
      return data.pageComparison || {
        pages: [],
        postTypesByPage: {},
        dominantTypes: {}
      };
    }

    // Filter posts by date and recalculate page comparison
    let posts = (data.posts || []);
    posts = posts.filter(p => {
      const postDate = p.publish_time?.slice(0, 10);
      if (!postDate) return true;
      if (startDate && postDate < startDate) return false;
      if (endDate && postDate > endDate) return false;
      return true;
    });

    // Aggregate by page
    const pageStats = {};
    const postTypesByPage = {};

    posts.forEach(p => {
      const pid = p.page_id;
      if (!pageStats[pid]) {
        pageStats[pid] = {
          page_id: pid,
          page_name: p.page_name,
          posts: 0,
          views: 0,
          reach: 0,
          reactions: 0,
          comments: 0,
          shares: 0,
          engagement: 0,
          fan_count: 0,
        };
        postTypesByPage[pid] = {};
      }
      pageStats[pid].posts++;
      pageStats[pid].views += p.views || 0;
      pageStats[pid].reach += p.reach || 0;
      pageStats[pid].reactions += p.reactions || 0;
      pageStats[pid].comments += p.comments || 0;
      pageStats[pid].shares += p.shares || 0;
      pageStats[pid].engagement += p.engagement || 0;

      // Track post types
      const ptype = p.post_type || 'Unknown';
      if (!postTypesByPage[pid][ptype]) {
        postTypesByPage[pid][ptype] = { type: ptype, count: 0, engagement: 0 };
      }
      postTypesByPage[pid][ptype].count++;
      postTypesByPage[pid][ptype].engagement += p.engagement || 0;
    });

    // Calculate averages, sort, and add rankings
    const totalEngagement = Object.values(pageStats).reduce((sum, p) => sum + p.engagement, 0);
    const pages = Object.values(pageStats)
      .map(p => ({
        ...p,
        avg_engagement: p.posts > 0 ? Math.round(p.engagement / p.posts) : 0,
        engagement_share: totalEngagement > 0 ? Math.round((p.engagement / totalEngagement) * 100) : 0,
      }))
      .sort((a, b) => b.engagement - a.engagement)
      .map((p, idx) => ({ ...p, rank: idx + 1 }));

    // Convert postTypesByPage to arrays and find dominant types
    const postTypesResult = {};
    const dominantTypes = {};
    Object.keys(postTypesByPage).forEach(pid => {
      const types = Object.values(postTypesByPage[pid]).sort((a, b) => b.count - a.count);
      postTypesResult[pid] = types;
      dominantTypes[pid] = types[0] || { type: 'N/A' };
    });

    return { pages, postTypesByPage: postTypesResult, dominantTypes };
  }
  return api.get('/stats/page-comparison/').then(res => res.data);
};'''

if old_getPageComparison in api_content:
    api_content = api_content.replace(old_getPageComparison, new_getPageComparison)
    with open(api_file, 'w', encoding='utf-8') as f:
        f.write(api_content)
    print("✓ Updated api.js with dateRange for getPageComparison")
else:
    print("⚠ api.js already updated or format changed")

# 2. Update Overlap.jsx - add DateFilter
overlap_file = os.path.join(PROJECT_DIR, 'frontend', 'src', 'pages', 'Overlap.jsx')
with open(overlap_file, 'r', encoding='utf-8') as f:
    overlap_content = f.read()

# Add import for DateFilter
old_import = "import { getPageComparison } from '../services/api';"
new_import = """import { getPageComparison } from '../services/api';
import DateFilter from '../components/DateFilter';"""

if 'DateFilter' not in overlap_content:
    overlap_content = overlap_content.replace(old_import, new_import)

    # Add dateRange state
    old_state = """const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState('engagement');"""

    new_state = """const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedMetric, setSelectedMetric] = useState('engagement');
  const [dateRange, setDateRange] = useState({ startDate: null, endDate: null });"""

    overlap_content = overlap_content.replace(old_state, new_state)

    # Update useEffect
    old_useEffect = """useEffect(() => {
    async function fetchData() {
      try {
        const data = await getPageComparison();
        setComparison(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);"""

    new_useEffect = """useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const data = await getPageComparison(dateRange);
        setComparison(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [dateRange]);"""

    overlap_content = overlap_content.replace(old_useEffect, new_useEffect)

    # Add DateFilter to UI
    old_header = """<div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Page Comparison</h1>
          <p className="text-sm text-gray-500">Compare performance across all JuanKada pages</p>
        </div>
      </div>"""

    new_header = """<div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Page Comparison</h1>
          <p className="text-sm text-gray-500">Compare performance across all JuanKada pages</p>
        </div>
        <DateFilter onFilterChange={setDateRange} />
      </div>"""

    overlap_content = overlap_content.replace(old_header, new_header)

    with open(overlap_file, 'w', encoding='utf-8') as f:
        f.write(overlap_content)
    print("✓ Updated Overlap.jsx with DateFilter")
else:
    print("⚠ Overlap.jsx already has DateFilter")

print("\nDone! Run 'npm run build' in frontend to build.")
