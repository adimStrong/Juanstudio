import { useState, useEffect, useMemo } from 'react';
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend
} from 'recharts';
import StatCard from '../components/StatCard';
import DateFilter from '../components/DateFilter';
import { getMonthlyReport, getDateBoundaries, getPostsByMonth } from '../services/api';

// ── Constants ────────────────────────────────────────────────────────────────

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16', '#a855f7', '#d946ef', '#0ea5e9'];
const TYPE_COLORS = { 'Photos': '#6366f1', 'Videos/Reels': '#22c55e', 'Links': '#f59e0b', 'Status': '#ef4444', 'Unknown': '#94a3b8' };
const METRIC_COLORS = { reactions: '#6366f1', comments: '#22c55e', shares: '#f59e0b', views: '#8b5cf6', reach: '#ec4899' };

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'pages', label: 'Pages' },
  { id: 'content', label: 'Content Type' },
  { id: 'trends', label: 'Trends' },
  { id: 'insights', label: 'Insights' },
];

const PAGE_PREFIX = 'JuanKada ';

// ── Helpers ──────────────────────────────────────────────────────────────────

const formatNumber = (num) => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num?.toLocaleString() || '0';
};

const formatMonth = (monthStr) => {
  if (!monthStr) return '';
  const [year, month] = monthStr.split('-');
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[parseInt(month) - 1]} ${year}`;
};

const shortName = (name) => (name || '').replace(PAGE_PREFIX, '');

function filterMonths(monthly, startDate, endDate) {
  if (!startDate && !endDate) return monthly;
  return monthly.filter(m => {
    const monthStart = m.month + '-01';
    const monthEnd = m.month + '-31';
    if (startDate && monthEnd < startDate) return false;
    if (endDate && monthStart > endDate) return false;
    return true;
  });
}

function getMetricChange(curr, prev, field) {
  if (!prev || !prev[field]) return null;
  return Math.round(((curr[field] - prev[field]) / prev[field]) * 100);
}

function generateInsights(filteredMonthly, monthlyByPage, postsByMonth) {
  if (!filteredMonthly || filteredMonthly.length === 0) return null;

  // filteredMonthly is newest-first
  const latest = filteredMonthly[0];
  const prev = filteredMonthly.length > 1 ? filteredMonthly[1] : null;

  const direction = latest.mom_change == null ? 'stable' : latest.mom_change > 0 ? 'up' : latest.mom_change < 0 ? 'down' : 'stable';

  // Metric changes
  const metricChanges = {};
  ['reactions', 'comments', 'shares', 'views', 'reach'].forEach(f => {
    metricChanges[f] = prev ? getMetricChange(latest, prev, f) : null;
  });

  // Page performance for latest month
  const pagePerf = [];
  Object.entries(monthlyByPage).forEach(([pageId, pdata]) => {
    const curr = pdata.data?.find(d => d.month === latest.month);
    if (curr) {
      pagePerf.push({ pageId, name: shortName(pdata.page_name), engagement: curr.engagement, mom_change: curr.mom_change });
    }
  });
  pagePerf.sort((a, b) => b.engagement - a.engagement);

  const topPage = pagePerf[0] || null;
  const biggestGainer = [...pagePerf].filter(p => p.mom_change != null).sort((a, b) => b.mom_change - a.mom_change)[0] || null;
  const biggestDropper = [...pagePerf].filter(p => p.mom_change != null).sort((a, b) => a.mom_change - b.mom_change)[0] || null;

  // Content type insights for latest month
  const latestContent = (postsByMonth || []).filter(p => p.month === latest.month);
  const topContentType = [...latestContent].sort((a, b) => b.engagement - a.engagement)[0] || null;

  // Recommendations
  const recommendations = [];
  if (direction === 'down') {
    recommendations.push('Engagement declined this month. Review content strategy and posting frequency.');
  }
  if (metricChanges.comments != null && metricChanges.comments < -10) {
    recommendations.push(`Comments dropped ${Math.abs(metricChanges.comments)}%. Consider more conversation-starting content (questions, polls).`);
  }
  if (metricChanges.shares != null && metricChanges.shares < -10) {
    recommendations.push(`Shares dropped ${Math.abs(metricChanges.shares)}%. Focus on shareable content (infographics, tips, memes).`);
  }
  if (metricChanges.views != null && metricChanges.views > 20) {
    recommendations.push(`Views grew ${metricChanges.views}% — great reach expansion. Keep investing in video content.`);
  }
  if (biggestDropper && biggestDropper.mom_change < -20) {
    recommendations.push(`${biggestDropper.name} dropped ${Math.abs(biggestDropper.mom_change)}%. Investigate content performance on this page.`);
  }
  if (biggestGainer && biggestGainer.mom_change > 20) {
    recommendations.push(`${biggestGainer.name} grew ${biggestGainer.mom_change}%. Replicate this page's strategy across others.`);
  }
  if (topContentType) {
    recommendations.push(`${topContentType.post_type} is the top-performing content type. Consider increasing its share.`);
  }
  if (latest.posts < (prev?.posts || 0) * 0.8) {
    recommendations.push('Posting volume dropped significantly. Maintain consistent posting schedule.');
  }
  if (direction === 'up' && recommendations.length === 0) {
    recommendations.push('Strong month! Continue current strategy and explore new content formats.');
  }

  return {
    direction,
    latestMonth: latest,
    prevMonth: prev,
    momChange: latest.mom_change,
    metricChanges,
    topPage,
    biggestGainer,
    biggestDropper,
    topContentType,
    pagePerf,
    recommendations: recommendations.slice(0, 5),
  };
}

// ── Sub-components ───────────────────────────────────────────────────────────

const MomBadge = ({ value }) => {
  if (value == null) return <span className="text-gray-300">-</span>;
  const isUp = value >= 0;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
      isUp ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
    }`}>
      {isUp ? '▲' : '▼'} {Math.abs(value)}%
    </span>
  );
};

const Medal = ({ rank }) => {
  if (rank === 1) return <span className="text-xl" title="1st">🥇</span>;
  if (rank === 2) return <span className="text-xl" title="2nd">🥈</span>;
  if (rank === 3) return <span className="text-xl" title="3rd">🥉</span>;
  return <span className="text-gray-400 text-sm font-medium">{rank}</span>;
};

// ── Main Component ───────────────────────────────────────────────────────────

export default function MonthlyReport() {
  const [data, setData] = useState(null);
  const [postsByMonth, setPostsByMonth] = useState([]);
  const [selectedMonth, setSelectedMonth] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [selectedPage, setSelectedPage] = useState(null);
  const [dateRange, setDateRange] = useState({ startDate: null, endDate: null });
  const [dateBoundaries, setDateBoundaries] = useState({ minDate: null, maxDate: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    Promise.all([getMonthlyReport(), getDateBoundaries(), getPostsByMonth()])
      .then(([result, bounds, pbm]) => {
        setData(result);
        setDateBoundaries(bounds);
        setPostsByMonth(pbm);
        if (result.monthly?.length > 0) {
          setSelectedMonth(result.monthly[0].month);
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filteredMonthly = useMemo(() => {
    if (!data?.monthly) return [];
    return filterMonths(data.monthly, dateRange.startDate, dateRange.endDate);
  }, [data, dateRange.startDate, dateRange.endDate]);

  useEffect(() => {
    if (filteredMonthly.length > 0) {
      const stillValid = filteredMonthly.some(m => m.month === selectedMonth);
      if (!stillValid) setSelectedMonth(filteredMonthly[0].month);
    }
  }, [filteredMonthly, selectedMonth]);

  // Chronological order (oldest first) for charts
  const chronological = useMemo(() => [...filteredMonthly].reverse(), [filteredMonthly]);

  const trendData = useMemo(() => chronological.map(m => ({
    month: formatMonth(m.month),
    rawMonth: m.month,
    reactions: m.reactions,
    comments: m.comments,
    shares: m.shares,
    engagement: m.engagement,
    views: m.views,
    reach: m.reach,
    avg_engagement: m.avg_engagement,
    posts: m.posts,
    mom_change: m.mom_change,
  })), [chronological]);

  const { monthlyByPage = {} } = data || {};

  // Per-page data for selected month
  const selectedMonthPages = useMemo(() => {
    if (!selectedMonth) return [];
    const pages = [];
    Object.entries(monthlyByPage).forEach(([pageId, pdata]) => {
      const monthData = pdata.data?.find(d => d.month === selectedMonth);
      if (monthData) {
        pages.push({ page_id: pageId, page_name: pdata.page_name || pageId, ...monthData });
      }
    });
    pages.sort((a, b) => b.engagement - a.engagement);
    return pages;
  }, [selectedMonth, monthlyByPage]);

  // Content type data grouped by month
  const contentByMonth = useMemo(() => {
    const months = chronological.map(m => m.month);
    const types = [...new Set(postsByMonth.map(p => p.post_type))];
    const chartData = months.map(month => {
      const row = { month: formatMonth(month), rawMonth: month };
      types.forEach(type => {
        const entry = postsByMonth.find(p => p.month === month && p.post_type === type);
        row[type] = entry?.count || 0;
        row[`${type}_eng`] = entry?.engagement || 0;
      });
      return row;
    });
    // Type summary for table (across all filtered months)
    const typeSummary = types.map(type => {
      const entries = postsByMonth.filter(p => p.post_type === type && months.includes(p.month));
      const count = entries.reduce((s, e) => s + e.count, 0);
      const engagement = entries.reduce((s, e) => s + e.engagement, 0);
      const views = entries.reduce((s, e) => s + e.views, 0);
      const reactions = entries.reduce((s, e) => s + e.reactions, 0);
      const comments = entries.reduce((s, e) => s + e.comments, 0);
      const shares = entries.reduce((s, e) => s + e.shares, 0);
      return { type, count, engagement, views, reactions, comments, shares, avg_eng: count > 0 ? Math.round(engagement / count) : 0 };
    }).sort((a, b) => b.engagement - a.engagement);
    return { chartData, types, typeSummary };
  }, [chronological, postsByMonth]);

  // Page trend data for the Trends tab (one line per page)
  const pageTrendData = useMemo(() => {
    const months = chronological.map(m => m.month);
    const pageNames = Object.entries(monthlyByPage).map(([, p]) => shortName(p.page_name));
    const chartData = months.map(month => {
      const row = { month: formatMonth(month), rawMonth: month };
      Object.entries(monthlyByPage).forEach(([, pdata]) => {
        const entry = pdata.data?.find(d => d.month === month);
        row[shortName(pdata.page_name)] = entry?.engagement || 0;
      });
      return row;
    });
    return { chartData, pageNames };
  }, [chronological, monthlyByPage]);

  // Heatmap data for trends tab (page × month matrix)
  const heatmapData = useMemo(() => {
    const months = chronological.map(m => m.month);
    const rows = [];
    Object.entries(monthlyByPage).forEach(([pageId, pdata]) => {
      const row = { name: shortName(pdata.page_name), pageId };
      months.forEach(month => {
        const entry = pdata.data?.find(d => d.month === month);
        row[month] = entry?.engagement || 0;
      });
      row.total = months.reduce((s, m) => s + (row[m] || 0), 0);
      rows.push(row);
    });
    rows.sort((a, b) => b.total - a.total);
    // Find max for color scale
    const allVals = rows.flatMap(r => months.map(m => r[m] || 0));
    const maxVal = Math.max(...allVals, 1);
    return { rows, months, maxVal };
  }, [chronological, monthlyByPage]);

  // Selected page drill-down data
  const pageDrillDown = useMemo(() => {
    if (!selectedPage) return null;
    const pdata = monthlyByPage[selectedPage];
    if (!pdata) return null;
    const months = chronological.map(m => m.month);
    const monthlyData = months.map(month => {
      const entry = pdata.data?.find(d => d.month === month);
      return entry ? { month: formatMonth(month), rawMonth: month, ...entry } : null;
    }).filter(Boolean);
    return { page_name: pdata.page_name, page_id: selectedPage, monthlyData };
  }, [selectedPage, monthlyByPage, chronological]);

  // Insights
  const insights = useMemo(() =>
    generateInsights(filteredMonthly, monthlyByPage, postsByMonth),
    [filteredMonthly, monthlyByPage, postsByMonth]
  );

  // Summary stats
  const totalPosts = filteredMonthly.reduce((s, m) => s + m.posts, 0);
  const totalEngagement = filteredMonthly.reduce((s, m) => s + m.engagement, 0);
  const totalReactions = filteredMonthly.reduce((s, m) => s + m.reactions, 0);
  const totalViews = filteredMonthly.reduce((s, m) => s + m.views, 0);
  const totalReach = filteredMonthly.reduce((s, m) => s + m.reach, 0);
  const latestMom = filteredMonthly.length > 0 ? filteredMonthly[0].mom_change : null;

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    </div>
  );

  if (error) return (
    <div className="bg-red-50 text-red-600 p-4 rounded-lg">Failed to load data: {error}</div>
  );

  // ── Tab: Overview ────────────────────────────────────────────────────────

  const renderOverview = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard title="Total Posts" value={totalPosts} icon="📝" color="indigo" subtitle={`${filteredMonthly.length} months`} />
        <StatCard title="Engagement" value={totalEngagement} icon="💬" color="green" subtitle={latestMom != null ? `MoM: ${latestMom > 0 ? '+' : ''}${latestMom}%` : ''} />
        <StatCard title="Reactions" value={totalReactions} icon="❤️" color="orange" />
        <StatCard title="Views" value={totalViews} icon="👁" color="blue" />
        <StatCard title="Reach" value={totalReach} icon="📡" color="purple" />
      </div>

      {/* Stacked bar: engagement composition by month */}
      {trendData.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Engagement Composition by Month</h2>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={formatNumber} />
              <Tooltip formatter={(value, name) => [formatNumber(value), name.charAt(0).toUpperCase() + name.slice(1)]} />
              <Legend />
              <Bar dataKey="reactions" stackId="eng" fill="#6366f1" name="Reactions" />
              <Bar dataKey="comments" stackId="eng" fill="#22c55e" name="Comments" />
              <Bar dataKey="shares" stackId="eng" fill="#f59e0b" name="Shares" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Monthly summary table */}
      {filteredMonthly.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Monthly Summary</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Month</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Posts</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Reactions</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Comments</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Shares</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Engagement</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Eng</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Views</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Reach</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">MoM</th>
                </tr>
              </thead>
              <tbody>
                {filteredMonthly.map(m => (
                  <tr
                    key={m.month}
                    className={`border-b border-gray-100 cursor-pointer transition-colors ${
                      selectedMonth === m.month ? 'bg-indigo-50' : 'hover:bg-gray-50'
                    }`}
                    onClick={() => setSelectedMonth(m.month)}
                  >
                    <td className="py-3 px-4 font-medium text-gray-900">{formatMonth(m.month)}</td>
                    <td className="text-right py-3 px-4">{m.posts.toLocaleString()}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.reactions)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.comments)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.shares)}</td>
                    <td className="text-right py-3 px-4 font-semibold">{formatNumber(m.engagement)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.avg_engagement)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.views)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.reach)}</td>
                    <td className="text-right py-3 px-4"><MomBadge value={m.mom_change} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  // ── Tab: Pages ───────────────────────────────────────────────────────────

  const renderPageDrillDown = () => {
    if (!pageDrillDown) return null;
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSelectedPage(null)}
            className="px-3 py-1.5 text-sm bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            ← Back to All Pages
          </button>
          <h2 className="text-lg font-semibold text-gray-900">{shortName(pageDrillDown.page_name)}</h2>
        </div>

        {/* Page monthly trend */}
        {pageDrillDown.monthlyData.length > 1 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Monthly Trend</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={pageDrillDown.monthlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={formatNumber} />
                <Tooltip formatter={(value, name) => [formatNumber(value), name.charAt(0).toUpperCase() + name.slice(1)]} />
                <Legend />
                <Line type="monotone" dataKey="engagement" stroke="#6366f1" strokeWidth={2} name="Engagement" dot={{ r: 4 }} />
                <Line type="monotone" dataKey="views" stroke="#22c55e" strokeWidth={2} name="Views" dot={{ r: 4 }} />
                <Line type="monotone" dataKey="reach" stroke="#f59e0b" strokeWidth={2} name="Reach" dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Engagement composition */}
        {pageDrillDown.monthlyData.length > 1 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-base font-semibold text-gray-900 mb-4">Engagement Breakdown</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={pageDrillDown.monthlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={formatNumber} />
                <Tooltip formatter={(value, name) => [formatNumber(value), name.charAt(0).toUpperCase() + name.slice(1)]} />
                <Legend />
                <Bar dataKey="reactions" stackId="eng" fill="#6366f1" name="Reactions" />
                <Bar dataKey="comments" stackId="eng" fill="#22c55e" name="Comments" />
                <Bar dataKey="shares" stackId="eng" fill="#f59e0b" name="Shares" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Page monthly table */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-base font-semibold text-gray-900 mb-4">Monthly Data</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Month</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Posts</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Reactions</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Comments</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Shares</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Engagement</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Views</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Reach</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">MoM</th>
                </tr>
              </thead>
              <tbody>
                {pageDrillDown.monthlyData.map(m => (
                  <tr key={m.rawMonth} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium text-gray-900">{m.month}</td>
                    <td className="text-right py-3 px-4">{m.posts}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.reactions)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.comments)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.shares)}</td>
                    <td className="text-right py-3 px-4 font-semibold">{formatNumber(m.engagement)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.views)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(m.reach)}</td>
                    <td className="text-right py-3 px-4"><MomBadge value={m.mom_change} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  const renderPages = () => {
    if (selectedPage) return renderPageDrillDown();

    const pageComparisonData = selectedMonthPages.map(p => ({
      name: shortName(p.page_name).length > 18 ? shortName(p.page_name).slice(0, 18) + '...' : shortName(p.page_name),
      engagement: p.engagement,
      views: p.views,
      reach: p.reach,
    }));

    return (
      <div className="space-y-6">
        {/* Month selector + bar chart */}
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              Page Comparison - {formatMonth(selectedMonth)}
            </h2>
            <select
              value={selectedMonth || ''}
              onChange={(e) => setSelectedMonth(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            >
              {filteredMonthly.map(m => (
                <option key={m.month} value={m.month}>{formatMonth(m.month)}</option>
              ))}
            </select>
          </div>

          {pageComparisonData.length > 0 && (
            <ResponsiveContainer width="100%" height={Math.max(300, pageComparisonData.length * 40)}>
              <BarChart data={pageComparisonData} layout="vertical" margin={{ left: 120 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={formatNumber} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} width={120} />
                <Tooltip formatter={(value, name) => [formatNumber(value), name.charAt(0).toUpperCase() + name.slice(1)]} />
                <Legend />
                <Bar dataKey="engagement" fill="#6366f1" name="Engagement" radius={[0, 4, 4, 0]} />
                <Bar dataKey="views" fill="#22c55e" name="Views" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Page performance table with rankings */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-1">
            Page Rankings - {formatMonth(selectedMonth)}
          </h2>
          <p className="text-gray-400 text-xs mb-4">Click a page name to view its monthly history</p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500 w-12">Rank</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Page</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Posts</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Avg React</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Comment</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Share</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Eng</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Views</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Reach</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">MoM</th>
                </tr>
              </thead>
              <tbody>
                {selectedMonthPages.map((p, i) => (
                  <tr key={p.page_id} className="border-b border-gray-100 hover:bg-indigo-50 transition-colors">
                    <td className="py-3 px-4"><Medal rank={i + 1} /></td>
                    <td
                      className="py-3 px-4 font-medium text-indigo-600 cursor-pointer hover:underline"
                      onClick={() => setSelectedPage(p.page_id)}
                    >
                      {shortName(p.page_name)}
                    </td>
                    <td className="text-right py-3 px-4">{p.posts}</td>
                    <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.reactions / p.posts)) : 0}</td>
                    <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.comments / p.posts)) : 0}</td>
                    <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.shares / p.posts)) : 0}</td>
                    <td className="text-right py-3 px-4 font-semibold">{formatNumber(p.avg_engagement)}</td>
                    <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.views / p.posts)) : 0}</td>
                    <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.reach / p.posts)) : 0}</td>
                    <td className="text-right py-3 px-4"><MomBadge value={p.mom_change} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
            {selectedMonthPages.length === 0 && (
              <p className="text-center text-gray-400 py-8">No page data for this month</p>
            )}
          </div>
        </div>
      </div>
    );
  };

  // ── Tab: Content Type ────────────────────────────────────────────────────

  const renderContentType = () => {
    const { chartData, types, typeSummary } = contentByMonth;

    return (
      <div className="space-y-6">
        {/* Post count by type per month */}
        {chartData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Post Type Distribution by Month</h2>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis />
                <Tooltip />
                <Legend />
                {types.map((type, i) => (
                  <Bar
                    key={type}
                    dataKey={type}
                    fill={TYPE_COLORS[type] || COLORS[i % COLORS.length]}
                    name={type}
                    stackId="types"
                    radius={i === types.length - 1 ? [4, 4, 0, 0] : undefined}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Engagement by type per month */}
        {chartData.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Engagement by Content Type</h2>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tickFormatter={formatNumber} />
                <Tooltip formatter={(v) => [formatNumber(v)]} />
                <Legend />
                {types.map((type, i) => (
                  <Bar
                    key={type}
                    dataKey={`${type}_eng`}
                    fill={TYPE_COLORS[type] || COLORS[i % COLORS.length]}
                    name={type}
                    stackId="eng"
                    radius={i === types.length - 1 ? [4, 4, 0, 0] : undefined}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Content type summary table */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Content Type Performance</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500">Type</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Posts</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Reactions</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Comments</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Shares</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Engagement</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Eng</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500">Views</th>
                </tr>
              </thead>
              <tbody>
                {typeSummary.map(t => (
                  <tr key={t.type} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium text-gray-900">
                      <span className="inline-block w-3 h-3 rounded-full mr-2" style={{ background: TYPE_COLORS[t.type] || '#94a3b8' }}></span>
                      {t.type}
                    </td>
                    <td className="text-right py-3 px-4">{t.count.toLocaleString()}</td>
                    <td className="text-right py-3 px-4">{formatNumber(t.reactions)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(t.comments)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(t.shares)}</td>
                    <td className="text-right py-3 px-4 font-semibold">{formatNumber(t.engagement)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(t.avg_eng)}</td>
                    <td className="text-right py-3 px-4">{formatNumber(t.views)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    );
  };

  // ── Tab: Trends ──────────────────────────────────────────────────────────

  const renderTrends = () => {
    if (trendData.length < 2) return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-400">
        Need at least 2 months of data to show trends.
      </div>
    );

    const { rows, months, maxVal } = heatmapData;

    const getCellBg = (val) => {
      if (!val) return 'bg-gray-50';
      const intensity = Math.min(val / maxVal, 1);
      if (intensity > 0.75) return 'bg-indigo-500 text-white';
      if (intensity > 0.5) return 'bg-indigo-400 text-white';
      if (intensity > 0.25) return 'bg-indigo-200 text-indigo-900';
      return 'bg-indigo-100 text-indigo-700';
    };

    return (
      <div className="space-y-6">
        {/* Metric trends */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Metric Trends</h2>
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={formatNumber} />
              <Tooltip formatter={(v, name) => [formatNumber(v), name.charAt(0).toUpperCase() + name.slice(1)]} />
              <Legend />
              <Line type="monotone" dataKey="reactions" stroke={METRIC_COLORS.reactions} strokeWidth={2} name="Reactions" dot={{ r: 3 }} />
              <Line type="monotone" dataKey="comments" stroke={METRIC_COLORS.comments} strokeWidth={2} name="Comments" dot={{ r: 3 }} />
              <Line type="monotone" dataKey="shares" stroke={METRIC_COLORS.shares} strokeWidth={2} name="Shares" dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Page engagement trends */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Page Engagement Trends</h2>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={pageTrendData.chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={formatNumber} />
              <Tooltip formatter={(v, name) => [formatNumber(v), name]} />
              <Legend />
              {pageTrendData.pageNames.map((name, i) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={COLORS[i % COLORS.length]}
                  strokeWidth={2}
                  name={name}
                  dot={{ r: 3 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Heatmap table */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Engagement Heatmap</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-3 font-medium text-gray-500">Page</th>
                  {months.map(m => (
                    <th key={m} className="text-center py-2 px-3 font-medium text-gray-500">{formatMonth(m)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map(row => (
                  <tr key={row.pageId} className="border-b border-gray-100">
                    <td className="py-2 px-3 font-medium text-gray-900 whitespace-nowrap">{row.name}</td>
                    {months.map(m => (
                      <td key={m} className={`text-center py-2 px-3 rounded ${getCellBg(row[m])}`}>
                        {row[m] ? formatNumber(row[m]) : '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex items-center gap-2 mt-3 text-xs text-gray-400">
            <span>Low</span>
            <span className="inline-block w-4 h-4 rounded bg-indigo-100"></span>
            <span className="inline-block w-4 h-4 rounded bg-indigo-200"></span>
            <span className="inline-block w-4 h-4 rounded bg-indigo-400"></span>
            <span className="inline-block w-4 h-4 rounded bg-indigo-500"></span>
            <span>High</span>
          </div>
        </div>
      </div>
    );
  };

  // ── Tab: Insights ────────────────────────────────────────────────────────

  const renderInsights = () => {
    if (!insights) return (
      <div className="bg-white rounded-lg shadow p-8 text-center text-gray-400">
        No data available for insights.
      </div>
    );

    const directionConfig = {
      up: { bg: 'bg-green-50 border-green-200', text: 'text-green-700', icon: '📈', label: 'Engagement is Growing' },
      down: { bg: 'bg-red-50 border-red-200', text: 'text-red-700', icon: '📉', label: 'Engagement is Declining' },
      stable: { bg: 'bg-blue-50 border-blue-200', text: 'text-blue-700', icon: '➡️', label: 'Engagement is Stable' },
    };
    const dc = directionConfig[insights.direction];

    return (
      <div className="space-y-6">
        {/* Executive summary */}
        <div className={`rounded-lg border p-6 ${dc.bg}`}>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-3xl">{dc.icon}</span>
            <div>
              <h2 className={`text-lg font-bold ${dc.text}`}>{dc.label}</h2>
              <p className="text-sm text-gray-600">
                {formatMonth(insights.latestMonth.month)}: {formatNumber(insights.latestMonth.engagement)} total engagement
                {insights.momChange != null && (
                  <> ({insights.momChange > 0 ? '+' : ''}{insights.momChange}% vs {insights.prevMonth ? formatMonth(insights.prevMonth.month) : 'prev'})</>
                )}
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
            <div className="text-center">
              <p className="text-xs text-gray-500 uppercase">Posts</p>
              <p className="text-lg font-bold text-gray-900">{insights.latestMonth.posts}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500 uppercase">Avg Engagement</p>
              <p className="text-lg font-bold text-gray-900">{formatNumber(insights.latestMonth.avg_engagement)}</p>
            </div>
            <div className="text-center">
              <p className="text-xs text-gray-500 uppercase">Views</p>
              <p className="text-lg font-bold text-gray-900">{formatNumber(insights.latestMonth.views)}</p>
            </div>
          </div>
        </div>

        {/* Metric changes */}
        {insights.prevMonth && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Metric Changes vs {formatMonth(insights.prevMonth.month)}</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {Object.entries(insights.metricChanges).map(([metric, change]) => (
                <div key={metric} className="text-center p-3 rounded-lg bg-gray-50">
                  <p className="text-xs text-gray-500 uppercase mb-1">{metric}</p>
                  <MomBadge value={change} />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Page highlights */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {insights.topPage && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">🏆</span>
                <h3 className="font-semibold text-gray-900">Top Performer</h3>
              </div>
              <p className="text-lg font-bold text-indigo-600">{insights.topPage.name}</p>
              <p className="text-sm text-gray-500">{formatNumber(insights.topPage.engagement)} engagement</p>
            </div>
          )}
          {insights.biggestGainer && insights.biggestGainer.mom_change > 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">🚀</span>
                <h3 className="font-semibold text-gray-900">Biggest Gainer</h3>
              </div>
              <p className="text-lg font-bold text-green-600">{insights.biggestGainer.name}</p>
              <p className="text-sm text-gray-500">+{insights.biggestGainer.mom_change}% MoM</p>
            </div>
          )}
          {insights.biggestDropper && insights.biggestDropper.mom_change < 0 && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">⚠️</span>
                <h3 className="font-semibold text-gray-900">Needs Attention</h3>
              </div>
              <p className="text-lg font-bold text-red-600">{insights.biggestDropper.name}</p>
              <p className="text-sm text-gray-500">{insights.biggestDropper.mom_change}% MoM</p>
            </div>
          )}
        </div>

        {/* Recommendations */}
        {insights.recommendations.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Recommendations</h2>
            <ul className="space-y-3">
              {insights.recommendations.map((rec, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xs font-bold">
                    {i + 1}
                  </span>
                  <p className="text-sm text-gray-700">{rec}</p>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Page performance summary */}
        {insights.pagePerf.length > 0 && (
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Page Performance - {formatMonth(insights.latestMonth.month)}</h2>
            <div className="space-y-2">
              {insights.pagePerf.map((p, i) => {
                const maxEng = insights.pagePerf[0]?.engagement || 1;
                const pct = Math.round((p.engagement / maxEng) * 100);
                return (
                  <div key={i} className="flex items-center gap-3">
                    <span className="w-24 text-sm font-medium text-gray-700 truncate">{p.name}</span>
                    <div className="flex-1 bg-gray-100 rounded-full h-5 relative overflow-hidden">
                      <div
                        className="h-full rounded-full bg-indigo-500 transition-all"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-sm text-gray-600 w-16 text-right">{formatNumber(p.engagement)}</span>
                    <span className="w-16"><MomBadge value={p.mom_change} /></span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  // ── Main Render ──────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Monthly Analysis</h1>
          <p className="text-gray-500 text-sm">Comprehensive monthly performance breakdown</p>
        </div>
        <DateFilter
          onDateChange={(r) => setDateRange(r)}
          minDate={dateBoundaries.minDate}
          maxDate={dateBoundaries.maxDate}
        />
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200">
          <nav className="flex overflow-x-auto -mb-px">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => { setActiveTab(tab.id); if (tab.id !== 'pages') setSelectedPage(null); }}
                className={`whitespace-nowrap px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-indigo-500 text-indigo-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && renderOverview()}
      {activeTab === 'pages' && renderPages()}
      {activeTab === 'content' && renderContentType()}
      {activeTab === 'trends' && renderTrends()}
      {activeTab === 'insights' && renderInsights()}
    </div>
  );
}
