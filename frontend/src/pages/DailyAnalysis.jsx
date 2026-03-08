import { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, ComposedChart
} from 'recharts';
import { getDateBoundaries } from '../services/api';

// ── Constants ────────────────────────────────────────────────────────────────

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6'];
const METRIC_COLORS = { reactions: '#6366f1', comments: '#22c55e', shares: '#f59e0b', views: '#8b5cf6', reach: '#ec4899' };
const PAGE_PREFIX = 'JuanKada ';

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'pages', label: 'Page Breakdown' },
  { id: 'content', label: 'Content Type' },
  { id: 'trends', label: 'Trends' },
  { id: 'insights', label: 'Insights' },
];

// ── Helpers ──────────────────────────────────────────────────────────────────

const formatNumber = (num) => {
  if (num == null || isNaN(num)) return '0';
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toLocaleString();
};

const shortName = (name) => (name || '').replace('JuanKada ', '').replace('JUANKada ', '').replace('Juankada ', '').replace('Juana Babe ', '');

const normalizeDate = (dateStr) => {
  if (!dateStr) return null;
  if (dateStr.length >= 10 && dateStr[4] === '-') return dateStr.slice(0, 10);
  if (dateStr.includes('/')) {
    const [m, d, y] = dateStr.split('/');
    return `${y.slice(0, 4)}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
  }
  return dateStr.slice(0, 10);
};

const formatDateLabel = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[d.getMonth()]} ${d.getDate()} (${days[d.getDay()]})`;
};

const shortDateLabel = (dateStr) => {
  if (!dateStr) return '';
  const d = new Date(dateStr + 'T00:00:00');
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[d.getMonth()]} ${d.getDate()}`;
};

const pctChange = (curr, prev) => {
  if (!prev || prev === 0) return null;
  return Math.round(((curr - prev) / Math.abs(prev)) * 100);
};

const DodBadge = ({ value, inverse = false }) => {
  if (value == null) return <span className="text-gray-400 text-xs">-</span>;
  const isUp = value >= 0;
  const isGood = inverse ? !isUp : isUp;
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-medium ${
      isGood ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
    }`}>
      {isUp ? '▲' : '▼'} {Math.abs(value)}%
    </span>
  );
};

const directionWord = (pct) => {
  if (pct == null) return 'unchanged';
  const abs = Math.abs(pct);
  if (abs < 1) return 'remained stable';
  const strength = abs > 30 ? 'significantly ' : abs > 10 ? 'slightly ' : '';
  return `${strength}${pct > 0 ? 'increased' : 'decreased'} by ${abs}%`;
};

// ── Data Loading ─────────────────────────────────────────────────────────────

let cachedData = null;
async function loadData() {
  if (!cachedData) {
    const resp = await fetch('/data/analytics-v2.json?t=' + Date.now());
    cachedData = await resp.json();
  }
  return cachedData;
}

function normalizePostType(type) {
  if (!type) return 'Unknown';
  const upper = type.toUpperCase();
  if (['VIDEO', 'VIDEOS', 'REEL', 'REELS'].includes(upper)) return 'Videos/Reels';
  if (['IMAGE', 'PHOTO', 'PHOTOS'].includes(upper)) return 'Photos';
  if (['LINK', 'LINKS'].includes(upper)) return 'Links';
  if (upper === 'TEXT') return 'Text';
  if (upper === 'LIVE') return 'Live';
  return type;
}

// ── Main Component ───────────────────────────────────────────────────────────

export default function DailyAnalysis() {
  const [rawData, setRawData] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedDateIdx, setSelectedDateIdx] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadData()
      .then(setRawData)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  // Build daily data sorted descending (newest first)
  const { dates, dailyAll, dailyByPage, pages, posts } = useMemo(() => {
    if (!rawData) return { dates: [], dailyAll: [], dailyByPage: {}, pages: [], posts: [] };
    const allDaily = (rawData.daily?.all || []).slice().sort((a, b) => b.date.localeCompare(a.date));
    const byPage = rawData.daily?.byPage || {};
    const pgs = rawData.pages || [];
    const ps = (rawData.posts || []).map(p => ({
      ...p,
      publish_date: normalizeDate(p.publish_time),
      post_type: normalizePostType(p.post_type),
      reactions: p.reactions ?? p.reactions_total ?? 0,
      comments: p.comments ?? p.comments_count ?? 0,
      shares: p.shares ?? p.shares_count ?? 0,
      engagement: p.engagement ?? p.total_engagement ?? 0,
      views: p.views ?? p.views_count ?? 0,
      reach: p.reach ?? p.reach_count ?? 0,
    }));
    return {
      dates: allDaily.map(d => d.date),
      dailyAll: allDaily,
      dailyByPage: byPage,
      pages: pgs,
      posts: ps,
    };
  }, [rawData]);

  const selDate = dates[selectedDateIdx] || null;
  const prevDate = dates[selectedDateIdx + 1] || null;

  const selDay = useMemo(() => dailyAll.find(d => d.date === selDate) || null, [dailyAll, selDate]);
  const prevDay = useMemo(() => dailyAll.find(d => d.date === prevDate) || null, [dailyAll, prevDate]);

  // Per-page data for selected date
  const pageDataForDate = useMemo(() => {
    if (!selDate) return [];
    return pages.map(pg => {
      const pageDaily = dailyByPage[pg.page_id] || [];
      const curr = pageDaily.find(d => d.date === selDate) || {};
      const prev = prevDate ? (pageDaily.find(d => d.date === prevDate) || {}) : {};
      return {
        page_id: pg.page_id,
        name: shortName(pg.page_name),
        posts: curr.posts || 0,
        engagement: curr.engagement || 0,
        reactions: curr.reactions || 0,
        comments: curr.comments || 0,
        shares: curr.shares || 0,
        views: curr.views || 0,
        reach: curr.reach || 0,
        prev_engagement: prev.engagement || 0,
        prev_posts: prev.posts || 0,
        prev_reactions: prev.reactions || 0,
        prev_comments: prev.comments || 0,
        prev_shares: prev.shares || 0,
        prev_views: prev.views || 0,
        prev_reach: prev.reach || 0,
      };
    }).sort((a, b) => b.engagement - a.engagement);
  }, [selDate, prevDate, pages, dailyByPage]);

  // Posts for selected date
  const postsForDate = useMemo(() => {
    if (!selDate) return [];
    return posts.filter(p => p.publish_date === selDate);
  }, [posts, selDate]);

  const prevPostsForDate = useMemo(() => {
    if (!prevDate) return [];
    return posts.filter(p => p.publish_date === prevDate);
  }, [posts, prevDate]);

  // 7-day rolling data (last 14 days for context)
  const trendData = useMemo(() => {
    if (!selDate || dailyAll.length === 0) return [];
    const idx = dailyAll.findIndex(d => d.date === selDate);
    if (idx < 0) return [];
    // Get last 14 entries from selected date
    const slice = dailyAll.slice(idx, Math.min(idx + 14, dailyAll.length)).reverse();
    return slice.map((d, i) => {
      const window = slice.slice(Math.max(0, i - 6), i + 1);
      return {
        date: shortDateLabel(d.date),
        fullDate: d.date,
        posts: d.posts || 0,
        engagement: d.engagement || 0,
        reactions: d.reactions || 0,
        comments: d.comments || 0,
        shares: d.shares || 0,
        views: d.views || 0,
        reach: d.reach || 0,
        avg_engagement: Math.round(window.reduce((s, x) => s + (x.engagement || 0), 0) / window.length),
        avg_posts: +(window.reduce((s, x) => s + (x.posts || 0), 0) / window.length).toFixed(1),
      };
    });
  }, [dailyAll, selDate]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
      </div>
    );
  }

  if (error || !selDay) {
    return <div className="bg-red-50 text-red-600 p-4 rounded-lg">Error: {error || 'No data'}</div>;
  }

  const metrics = [
    { key: 'posts', label: 'Posts', icon: '📝', color: 'indigo' },
    { key: 'engagement', label: 'Engagement', icon: '🔥', color: 'orange' },
    { key: 'reactions', label: 'Reactions', icon: '👍', color: 'blue' },
    { key: 'comments', label: 'Comments', icon: '💬', color: 'green' },
    { key: 'shares', label: 'Shares', icon: '🔄', color: 'purple' },
    { key: 'views', label: 'Views', icon: '👁', color: 'cyan' },
    { key: 'reach', label: 'Reach', icon: '📡', color: 'pink' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Daily Analysis</h1>
          <p className="text-sm text-gray-500">
            Day-over-day performance comparison
            {prevDate && <span> &middot; Comparing vs {formatDateLabel(prevDate)}</span>}
          </p>
        </div>
        <select
          value={selectedDateIdx}
          onChange={e => setSelectedDateIdx(Number(e.target.value))}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white shadow-sm"
        >
          {dates.map((d, i) => (
            <option key={d} value={i}>{formatDateLabel(d)}</option>
          ))}
        </select>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 overflow-x-auto">
        <nav className="flex -mb-px space-x-4 min-w-max">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-3 border-b-2 text-sm font-medium whitespace-nowrap transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <OverviewTab selDay={selDay} prevDay={prevDay} metrics={metrics} selDate={selDate} prevDate={prevDate} pageDataForDate={pageDataForDate} postsForDate={postsForDate} />
      )}
      {activeTab === 'pages' && (
        <PageBreakdownTab pageDataForDate={pageDataForDate} selDate={selDate} prevDate={prevDate} />
      )}
      {activeTab === 'content' && (
        <ContentTypeTab postsForDate={postsForDate} prevPostsForDate={prevPostsForDate} selDate={selDate} prevDate={prevDate} />
      )}
      {activeTab === 'trends' && (
        <TrendsTab trendData={trendData} selDate={selDate} pageDataForDate={pageDataForDate} dailyByPage={dailyByPage} dailyAll={dailyAll} pages={pages} />
      )}
      {activeTab === 'insights' && (
        <InsightsTab selDay={selDay} prevDay={prevDay} selDate={selDate} pageDataForDate={pageDataForDate} postsForDate={postsForDate} />
      )}
    </div>
  );
}

// ── Tab: Overview ────────────────────────────────────────────────────────────

function OverviewTab({ selDay, prevDay, metrics, selDate, prevDate, pageDataForDate, postsForDate }) {
  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
        {metrics.map(m => {
          const curr = selDay[m.key] || 0;
          const prev = prevDay?.[m.key] || 0;
          const change = pctChange(curr, prev);
          return (
            <div key={m.key} className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-500">{m.label}</span>
                <span className="text-lg">{m.icon}</span>
              </div>
              <p className="text-2xl font-bold text-gray-900">{formatNumber(curr)}</p>
              <div className="flex items-center gap-2 mt-1">
                <DodBadge value={change} />
                {prevDay && <span className="text-xs text-gray-400">vs {formatNumber(prev)}</span>}
              </div>
            </div>
          );
        })}
      </div>

      {/* DoD Comparison Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b">
          <h3 className="text-sm font-semibold text-gray-700">Day-over-Day Comparison</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-600">
                <th className="px-4 py-2 text-left font-medium">Metric</th>
                <th className="px-4 py-2 text-right font-medium">{prevDate ? formatDateLabel(prevDate) : 'Prev'}</th>
                <th className="px-4 py-2 text-right font-medium">{formatDateLabel(selDate)}</th>
                <th className="px-4 py-2 text-right font-medium">Change</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {metrics.map(m => {
                const curr = selDay[m.key] || 0;
                const prev = prevDay?.[m.key] || 0;
                return (
                  <tr key={m.key} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-medium text-gray-700">{m.icon} {m.label}</td>
                    <td className="px-4 py-2 text-right text-gray-500">{formatNumber(prev)}</td>
                    <td className="px-4 py-2 text-right font-semibold text-gray-900">{formatNumber(curr)}</td>
                    <td className="px-4 py-2 text-right"><DodBadge value={pctChange(curr, prev)} /></td>
                  </tr>
                );
              })}
              {/* Avg engagement per post */}
              <tr className="hover:bg-gray-50 bg-indigo-50/50">
                <td className="px-4 py-2 font-medium text-gray-700">📊 Avg Engagement/Post</td>
                <td className="px-4 py-2 text-right text-gray-500">
                  {prevDay ? formatNumber(Math.round((prevDay.engagement || 0) / Math.max(prevDay.posts || 1, 1))) : '-'}
                </td>
                <td className="px-4 py-2 text-right font-semibold text-gray-900">
                  {formatNumber(Math.round((selDay.engagement || 0) / Math.max(selDay.posts || 1, 1)))}
                </td>
                <td className="px-4 py-2 text-right">
                  <DodBadge value={pctChange(
                    (selDay.engagement || 0) / Math.max(selDay.posts || 1, 1),
                    prevDay ? (prevDay.engagement || 0) / Math.max(prevDay.posts || 1, 1) : 0
                  )} />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Posts of the Day */}
      {postsForDate.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-4 py-3 bg-gray-50 border-b">
            <h3 className="text-sm font-semibold text-gray-700">Top Posts — {formatDateLabel(selDate)}</h3>
          </div>
          <div className="divide-y divide-gray-100">
            {postsForDate
              .sort((a, b) => b.engagement - a.engagement)
              .slice(0, 5)
              .map((post, i) => (
                <div key={i} className="px-4 py-3 flex items-start gap-3">
                  <span className="text-lg mt-0.5">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-800 truncate">{post.title || post.message || '(No title)'}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>{shortName(post.page_name)}</span>
                      <span className="px-1.5 py-0.5 bg-gray-100 rounded">{post.post_type}</span>
                      <span>👍 {post.reactions}</span>
                      <span>💬 {post.comments}</span>
                      <span>🔄 {post.shares}</span>
                      <span className="font-medium text-indigo-600">Eng: {formatNumber(post.engagement)}</span>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Page Rankings */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b">
          <h3 className="text-sm font-semibold text-gray-700">Page Rankings</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-600">
                <th className="px-4 py-2 text-left font-medium">#</th>
                <th className="px-4 py-2 text-left font-medium">Page</th>
                <th className="px-4 py-2 text-right font-medium">Posts</th>
                <th className="px-4 py-2 text-right font-medium">Engagement</th>
                <th className="px-4 py-2 text-right font-medium">DoD</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {pageDataForDate.map((pg, i) => (
                <tr key={pg.page_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1}</td>
                  <td className="px-4 py-2 font-medium text-gray-800">{pg.name}</td>
                  <td className="px-4 py-2 text-right text-gray-600">{pg.posts}</td>
                  <td className="px-4 py-2 text-right font-semibold">{formatNumber(pg.engagement)}</td>
                  <td className="px-4 py-2 text-right"><DodBadge value={pctChange(pg.engagement, pg.prev_engagement)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ── Tab: Page Breakdown ──────────────────────────────────────────────────────

function PageBreakdownTab({ pageDataForDate, selDate, prevDate }) {
  const metricKeys = [
    { key: 'engagement', label: 'Engagement' },
    { key: 'reactions', label: 'Reactions' },
    { key: 'comments', label: 'Comments' },
    { key: 'shares', label: 'Shares' },
    { key: 'views', label: 'Views' },
    { key: 'reach', label: 'Reach' },
  ];

  // Chart data
  const chartData = pageDataForDate.map(pg => ({
    name: pg.name,
    engagement: pg.engagement,
    prev_engagement: pg.prev_engagement,
  }));

  return (
    <div className="space-y-6">
      {/* Engagement Bar Chart - Current vs Previous */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Engagement by Page — DoD Comparison</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip formatter={v => formatNumber(v)} />
            <Legend />
            {prevDate && <Bar dataKey="prev_engagement" name={formatDateLabel(prevDate)} fill="#cbd5e1" radius={[4, 4, 0, 0]} />}
            <Bar dataKey="engagement" name={formatDateLabel(selDate)} fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Full Metrics Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b">
          <h3 className="text-sm font-semibold text-gray-700">All Pages — Detailed Metrics</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-600">
                <th className="px-3 py-2 text-left font-medium">Page</th>
                <th className="px-3 py-2 text-center font-medium">Posts</th>
                {metricKeys.map(m => (
                  <th key={m.key} className="px-3 py-2 text-right font-medium">{m.label}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {pageDataForDate.map(pg => (
                <tr key={pg.page_id} className="hover:bg-gray-50">
                  <td className="px-3 py-2 font-medium text-gray-800">{pg.name}</td>
                  <td className="px-3 py-2 text-center text-gray-600">
                    {pg.posts}
                    {prevDate && pg.prev_posts > 0 && (
                      <span className="ml-1"><DodBadge value={pctChange(pg.posts, pg.prev_posts)} /></span>
                    )}
                  </td>
                  {metricKeys.map(m => (
                    <td key={m.key} className="px-3 py-2 text-right">
                      <span className="font-medium text-gray-900">{formatNumber(pg[m.key])}</span>
                      {prevDate && pg[`prev_${m.key}`] > 0 && (
                        <div className="mt-0.5"><DodBadge value={pctChange(pg[m.key], pg[`prev_${m.key}`])} /></div>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
              {/* Total row */}
              <tr className="bg-indigo-50 font-semibold">
                <td className="px-3 py-2 text-gray-800">TOTAL</td>
                <td className="px-3 py-2 text-center">{pageDataForDate.reduce((s, p) => s + p.posts, 0)}</td>
                {metricKeys.map(m => (
                  <td key={m.key} className="px-3 py-2 text-right text-gray-900">
                    {formatNumber(pageDataForDate.reduce((s, p) => s + p[m.key], 0))}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Individual Page Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {pageDataForDate.map((pg, i) => (
          <div key={pg.page_id} className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="font-semibold text-gray-800">{pg.name}</h4>
              <span className="text-lg">{i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : ''}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Posts</span>
                <span className="font-medium">{pg.posts}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Engagement</span>
                <span className="font-medium">{formatNumber(pg.engagement)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Reactions</span>
                <span className="font-medium">{formatNumber(pg.reactions)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Comments</span>
                <span className="font-medium">{formatNumber(pg.comments)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Shares</span>
                <span className="font-medium">{formatNumber(pg.shares)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Views</span>
                <span className="font-medium">{formatNumber(pg.views)}</span>
              </div>
            </div>
            {prevDate && (
              <div className="mt-3 pt-2 border-t flex items-center gap-2 text-xs text-gray-500">
                <span>vs {formatDateLabel(prevDate)}:</span>
                <DodBadge value={pctChange(pg.engagement, pg.prev_engagement)} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Tab: Content Type ────────────────────────────────────────────────────────

function ContentTypeTab({ postsForDate, prevPostsForDate, selDate, prevDate }) {
  const aggregate = (postList) => {
    const byType = {};
    postList.forEach(p => {
      const t = p.post_type || 'Unknown';
      if (!byType[t]) byType[t] = { type: t, count: 0, engagement: 0, reactions: 0, comments: 0, shares: 0, views: 0 };
      byType[t].count++;
      byType[t].engagement += p.engagement;
      byType[t].reactions += p.reactions;
      byType[t].comments += p.comments;
      byType[t].shares += p.shares;
      byType[t].views += p.views;
    });
    return Object.values(byType).sort((a, b) => b.engagement - a.engagement);
  };

  const currTypes = aggregate(postsForDate);
  const prevTypes = aggregate(prevPostsForDate);

  const TYPE_COLORS = { 'Photos': '#6366f1', 'Videos/Reels': '#22c55e', 'Links': '#f59e0b', 'Text': '#ef4444', 'Live': '#8b5cf6', 'Unknown': '#94a3b8' };

  return (
    <div className="space-y-6">
      {/* Content Type Distribution Bar */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Content Type Distribution</h3>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={currTypes}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="type" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip formatter={v => formatNumber(v)} />
            <Bar dataKey="count" name="Posts" fill="#6366f1" radius={[4, 4, 0, 0]} />
            <Bar dataKey="engagement" name="Engagement" fill="#22c55e" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Content Comparison Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b">
          <h3 className="text-sm font-semibold text-gray-700">Content Type — DoD Comparison</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-gray-600">
                <th className="px-4 py-2 text-left font-medium">Type</th>
                <th className="px-4 py-2 text-right font-medium">Posts</th>
                <th className="px-4 py-2 text-right font-medium">Engagement</th>
                <th className="px-4 py-2 text-right font-medium">Avg Eng/Post</th>
                <th className="px-4 py-2 text-right font-medium">Reactions</th>
                <th className="px-4 py-2 text-right font-medium">Comments</th>
                <th className="px-4 py-2 text-right font-medium">Shares</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {currTypes.map(ct => {
                const prev = prevTypes.find(p => p.type === ct.type) || {};
                const avgEng = ct.count > 0 ? Math.round(ct.engagement / ct.count) : 0;
                const prevAvg = (prev.count || 0) > 0 ? Math.round((prev.engagement || 0) / prev.count) : 0;
                return (
                  <tr key={ct.type} className="hover:bg-gray-50">
                    <td className="px-4 py-2">
                      <span className="inline-block w-3 h-3 rounded-full mr-2" style={{ backgroundColor: TYPE_COLORS[ct.type] || '#94a3b8' }}></span>
                      <span className="font-medium text-gray-800">{ct.type}</span>
                    </td>
                    <td className="px-4 py-2 text-right">
                      {ct.count} <DodBadge value={pctChange(ct.count, prev.count)} />
                    </td>
                    <td className="px-4 py-2 text-right">
                      {formatNumber(ct.engagement)} <DodBadge value={pctChange(ct.engagement, prev.engagement)} />
                    </td>
                    <td className="px-4 py-2 text-right">
                      {formatNumber(avgEng)} <DodBadge value={pctChange(avgEng, prevAvg)} />
                    </td>
                    <td className="px-4 py-2 text-right">{formatNumber(ct.reactions)}</td>
                    <td className="px-4 py-2 text-right">{formatNumber(ct.comments)}</td>
                    <td className="px-4 py-2 text-right">{formatNumber(ct.shares)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Post per Type */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-4 py-3 bg-gray-50 border-b">
          <h3 className="text-sm font-semibold text-gray-700">Top Post per Content Type</h3>
        </div>
        <div className="divide-y divide-gray-100">
          {currTypes.map(ct => {
            const topPost = postsForDate
              .filter(p => p.post_type === ct.type)
              .sort((a, b) => b.engagement - a.engagement)[0];
            if (!topPost) return null;
            return (
              <div key={ct.type} className="px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="inline-block w-3 h-3 rounded-full" style={{ backgroundColor: TYPE_COLORS[ct.type] || '#94a3b8' }}></span>
                  <span className="text-sm font-medium text-gray-700">{ct.type}</span>
                </div>
                <p className="text-sm text-gray-600 truncate">{topPost.title || topPost.message || '(No title)'}</p>
                <div className="flex gap-3 mt-1 text-xs text-gray-500">
                  <span>{shortName(topPost.page_name)}</span>
                  <span>👍 {topPost.reactions}</span>
                  <span>💬 {topPost.comments}</span>
                  <span>🔄 {topPost.shares}</span>
                  <span className="text-indigo-600 font-medium">Eng: {formatNumber(topPost.engagement)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ── Tab: Trends ──────────────────────────────────────────────────────────────

function TrendsTab({ trendData, selDate, pageDataForDate, dailyByPage, dailyAll, pages }) {
  const [trendMetric, setTrendMetric] = useState('engagement');

  // Per-page trend (last 14 days)
  const pageTrendData = useMemo(() => {
    if (!selDate || !dailyAll.length) return [];
    const idx = dailyAll.findIndex(d => d.date === selDate);
    if (idx < 0) return [];
    const dateSlice = dailyAll.slice(idx, Math.min(idx + 14, dailyAll.length)).reverse().map(d => d.date);
    return dateSlice.map(date => {
      const row = { date: shortDateLabel(date) };
      pages.forEach(pg => {
        const pageDaily = dailyByPage[pg.page_id] || [];
        const dayData = pageDaily.find(d => d.date === date);
        row[shortName(pg.page_name)] = dayData?.[trendMetric] || 0;
      });
      return row;
    });
  }, [selDate, dailyAll, dailyByPage, pages, trendMetric]);

  const pageNames = pages.map(p => shortName(p.page_name));

  return (
    <div className="space-y-6">
      {/* Engagement + Posts Dual Chart */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-4">Engagement & Posts — Last 14 Days</h3>
        <ResponsiveContainer width="100%" height={300}>
          <ComposedChart data={trendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} />
            <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
            <Tooltip formatter={v => formatNumber(v)} />
            <Legend />
            <Bar yAxisId="left" dataKey="engagement" name="Engagement" fill="#6366f1" radius={[4, 4, 0, 0]} opacity={0.8} />
            <Line yAxisId="right" dataKey="posts" name="Posts" stroke="#22c55e" strokeWidth={2} dot={{ r: 3 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* 7-Day Rolling Average */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Engagement vs 7D Rolling Avg</h3>
          <ResponsiveContainer width="100%" height={250}>
            <ComposedChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip formatter={v => formatNumber(v)} />
              <Bar dataKey="engagement" name="Daily" fill="#c7d2fe" radius={[3, 3, 0, 0]} />
              <Line dataKey="avg_engagement" name="7D Avg" stroke="#4338ca" strokeWidth={2} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Engagement Breakdown</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip formatter={v => formatNumber(v)} />
              <Legend />
              <Bar dataKey="reactions" name="Reactions" stackId="a" fill="#6366f1" />
              <Bar dataKey="comments" name="Comments" stackId="a" fill="#22c55e" />
              <Bar dataKey="shares" name="Shares" stackId="a" fill="#f59e0b" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Per-Page Trend */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700">Per-Page Trend</h3>
          <select
            value={trendMetric}
            onChange={e => setTrendMetric(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1 text-sm"
          >
            <option value="engagement">Engagement</option>
            <option value="reactions">Reactions</option>
            <option value="comments">Comments</option>
            <option value="shares">Shares</option>
            <option value="views">Views</option>
            <option value="posts">Posts</option>
          </select>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={pageTrendData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip formatter={v => formatNumber(v)} />
            <Legend />
            {pageNames.map((name, i) => (
              <Line
                key={name}
                dataKey={name}
                stroke={COLORS[i % COLORS.length]}
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ── Tab: Insights ────────────────────────────────────────────────────────────

function InsightsTab({ selDay, prevDay, selDate, pageDataForDate, postsForDate }) {
  const engChange = pctChange(selDay.engagement, prevDay?.engagement);
  const postChange = pctChange(selDay.posts, prevDay?.posts);
  const reactChange = pctChange(selDay.reactions, prevDay?.reactions);
  const commentChange = pctChange(selDay.comments, prevDay?.comments);
  const shareChange = pctChange(selDay.shares, prevDay?.shares);

  const topPage = pageDataForDate[0] || null;
  const biggestGainer = [...pageDataForDate]
    .filter(p => p.prev_engagement > 0)
    .sort((a, b) => pctChange(b.engagement, b.prev_engagement) - pctChange(a.engagement, a.prev_engagement))[0] || null;
  const biggestDropper = [...pageDataForDate]
    .filter(p => p.prev_engagement > 0)
    .sort((a, b) => pctChange(a.engagement, a.prev_engagement) - pctChange(b.engagement, b.prev_engagement))[0] || null;

  const topPost = postsForDate.sort((a, b) => b.engagement - a.engagement)[0] || null;

  // Generate recommendations
  const recommendations = [];
  if (engChange != null && engChange < -10) {
    recommendations.push('Engagement declined. Review content strategy and posting schedule.');
  }
  if (commentChange != null && commentChange < -20) {
    recommendations.push(`Comments dropped ${Math.abs(commentChange)}%. Try more interactive content (questions, polls, calls-to-action).`);
  }
  if (shareChange != null && shareChange < -20) {
    recommendations.push(`Shares dropped ${Math.abs(shareChange)}%. Focus on shareable formats (tips, infographics, memes).`);
  }
  if (engChange != null && engChange > 20) {
    recommendations.push(`Strong engagement growth (+${engChange}%). Analyze what worked and replicate across pages.`);
  }
  if (postChange != null && postChange < -30) {
    recommendations.push('Posting volume dropped significantly. Maintain consistent posting frequency.');
  }
  if (biggestDropper && pctChange(biggestDropper.engagement, biggestDropper.prev_engagement) < -30) {
    recommendations.push(`${biggestDropper.name} had a significant drop. Investigate content performance on this page.`);
  }
  if (biggestGainer && pctChange(biggestGainer.engagement, biggestGainer.prev_engagement) > 30) {
    recommendations.push(`${biggestGainer.name} showed strong growth. Study and replicate its strategy.`);
  }
  if (recommendations.length === 0) {
    recommendations.push('Performance is stable. Continue monitoring and optimizing content strategy.');
  }

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Executive Summary</h3>
        <div className="prose prose-sm text-gray-600 space-y-2">
          <p>
            On <strong>{formatDateLabel(selDate)}</strong>, a total of <strong>{selDay.posts}</strong> posts
            were published generating <strong>{formatNumber(selDay.engagement)}</strong> total engagement
            ({formatNumber(selDay.reactions)} reactions, {formatNumber(selDay.comments)} comments, {formatNumber(selDay.shares)} shares).
          </p>
          {prevDay && (
            <p>
              Compared to the previous day, engagement {directionWord(engChange)}.
              Posting volume {directionWord(postChange)}.
              Reactions {directionWord(reactChange)} while comments {directionWord(commentChange)}.
            </p>
          )}
        </div>
      </div>

      {/* Page Performance Insights */}
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Page Performance</h3>
        <div className="space-y-3 text-sm text-gray-600">
          {topPage && (
            <div className="flex items-start gap-2">
              <span className="text-lg">🥇</span>
              <p><strong>{topPage.name}</strong> led with {formatNumber(topPage.engagement)} engagement from {topPage.posts} posts.</p>
            </div>
          )}
          {biggestGainer && pctChange(biggestGainer.engagement, biggestGainer.prev_engagement) > 0 && (
            <div className="flex items-start gap-2">
              <span className="text-lg">📈</span>
              <p><strong>{biggestGainer.name}</strong> was the biggest gainer with <DodBadge value={pctChange(biggestGainer.engagement, biggestGainer.prev_engagement)} /> engagement growth.</p>
            </div>
          )}
          {biggestDropper && pctChange(biggestDropper.engagement, biggestDropper.prev_engagement) < 0 && (
            <div className="flex items-start gap-2">
              <span className="text-lg">📉</span>
              <p><strong>{biggestDropper.name}</strong> had the biggest decline with <DodBadge value={pctChange(biggestDropper.engagement, biggestDropper.prev_engagement)} /> engagement change.</p>
            </div>
          )}
        </div>
      </div>

      {/* Page DoD Changes */}
      {prevDay && (
        <div className="bg-white rounded-lg shadow p-5">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Day-over-Day Page Changes</h3>
          <div className="space-y-2">
            {pageDataForDate.filter(p => p.engagement > 0 || p.prev_engagement > 0).map(pg => {
              const change = pctChange(pg.engagement, pg.prev_engagement);
              const diff = pg.engagement - pg.prev_engagement;
              return (
                <div key={pg.page_id} className="flex items-center justify-between text-sm py-1.5 border-b border-gray-50">
                  <span className="font-medium text-gray-700">{pg.name}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-gray-500">{formatNumber(pg.prev_engagement)} → {formatNumber(pg.engagement)}</span>
                    <span className={`font-medium ${diff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {diff >= 0 ? '+' : ''}{formatNumber(diff)}
                    </span>
                    <DodBadge value={change} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Top Post of the Day */}
      {topPost && (
        <div className="bg-white rounded-lg shadow p-5">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Top Post of the Day</h3>
          <div className="bg-indigo-50 rounded-lg p-4">
            <p className="text-sm text-gray-700 mb-2">{topPost.title || topPost.message || '(No title)'}</p>
            <div className="flex flex-wrap gap-3 text-xs text-gray-600">
              <span className="font-medium">{shortName(topPost.page_name)}</span>
              <span className="bg-white px-2 py-0.5 rounded">{topPost.post_type}</span>
              <span>👍 {formatNumber(topPost.reactions)}</span>
              <span>💬 {formatNumber(topPost.comments)}</span>
              <span>🔄 {formatNumber(topPost.shares)}</span>
              <span>👁 {formatNumber(topPost.views)}</span>
              <span className="font-bold text-indigo-600">Total: {formatNumber(topPost.engagement)}</span>
            </div>
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div className="bg-white rounded-lg shadow p-5">
        <h3 className="text-lg font-semibold text-gray-800 mb-3">Recommendations</h3>
        <div className="space-y-2">
          {recommendations.map((rec, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-gray-600">
              <span className="text-amber-500 mt-0.5">💡</span>
              <p>{rec}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
