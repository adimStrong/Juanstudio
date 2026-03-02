import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, Cell
} from 'recharts';
import StatCard from '../components/StatCard';
import DateFilter from '../components/DateFilter';
import { getMonthlyReport, getDateBoundaries } from '../services/api';

const COLORS = ['#6366f1', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16', '#a855f7', '#d946ef', '#0ea5e9'];

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

export default function MonthlyReport() {
  const [data, setData] = useState(null);
  const [selectedMonth, setSelectedMonth] = useState(null);
  const [dateRange, setDateRange] = useState({ startDate: null, endDate: null });
  const [dateBoundaries, setDateBoundaries] = useState({ minDate: null, maxDate: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getDateBoundaries().then(setDateBoundaries).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    getMonthlyReport(dateRange)
      .then(result => {
        setData(result);
        // Always reset selectedMonth to first month matching the new filter
        const filtered = (result.monthly || []).filter(m => {
          if (!dateRange.startDate && !dateRange.endDate) return true;
          const monthStart = m.month + '-01';
          const monthEnd = m.month + '-31';
          if (dateRange.startDate && monthEnd < dateRange.startDate) return false;
          if (dateRange.endDate && monthStart > dateRange.endDate) return false;
          return true;
        });
        if (filtered.length > 0) {
          setSelectedMonth(filtered[0].month);
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [dateRange]);

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
    </div>
  );

  if (error) return (
    <div className="bg-red-50 text-red-600 p-4 rounded-lg">Failed to load data: {error}</div>
  );

  const { monthly = [], monthlyByPage = {} } = data || {};

  // Filter monthly data by date range
  const filteredMonthly = monthly.filter(m => {
    if (!dateRange.startDate && !dateRange.endDate) return true;
    const monthStart = m.month + '-01';
    const monthEnd = m.month + '-31';
    if (dateRange.startDate && monthEnd < dateRange.startDate) return false;
    if (dateRange.endDate && monthStart > dateRange.endDate) return false;
    return true;
  });

  // Summary stats across all filtered months
  const totalPosts = filteredMonthly.reduce((s, m) => s + m.posts, 0);
  const totalEngagement = filteredMonthly.reduce((s, m) => s + m.engagement, 0);
  const totalViews = filteredMonthly.reduce((s, m) => s + m.views, 0);
  const totalReach = filteredMonthly.reduce((s, m) => s + m.reach, 0);
  const avgEngagement = totalPosts > 0 ? Math.round(totalEngagement / totalPosts) : 0;
  const avgViews = totalPosts > 0 ? Math.round(totalViews / totalPosts) : 0;
  const avgReach = totalPosts > 0 ? Math.round(totalReach / totalPosts) : 0;

  // Trend chart data (oldest first for chart)
  const trendData = [...filteredMonthly].reverse().map(m => ({
    month: formatMonth(m.month),
    rawMonth: m.month,
    engagement: m.engagement,
    views: m.views,
    reach: m.reach,
    avg_engagement: m.avg_engagement,
    mom_change: m.mom_change
  }));

  // Per-page data for selected month
  const selectedMonthPages = [];
  if (selectedMonth) {
    Object.entries(monthlyByPage).forEach(([pageId, pdata]) => {
      const monthData = pdata.data?.find(d => d.month === selectedMonth);
      if (monthData) {
        selectedMonthPages.push({
          page_id: pageId,
          page_name: pdata.page_name || pageId,
          ...monthData
        });
      }
    });
    selectedMonthPages.sort((a, b) => b.engagement - a.engagement);
  }

  // Bar chart data for page comparison within selected month
  const pageComparisonData = selectedMonthPages.map(p => ({
    name: (p.page_name || '').length > 15 ? (p.page_name || '').slice(0, 15) + '...' : (p.page_name || ''),
    engagement: p.engagement,
    views: p.views,
    reach: p.reach,
    posts: p.posts
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Monthly Report</h1>
          <p className="text-gray-500 text-sm">Monthly averages and per-page breakdown</p>
        </div>
        <DateFilter
          onDateChange={setDateRange}
          minDate={dateBoundaries.minDate}
          maxDate={dateBoundaries.maxDate}
        />
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Total Posts" value={totalPosts} icon="📝" color="indigo" subtitle={`${filteredMonthly.length} months`} />
        <StatCard title="Avg Engagement / Post" value={avgEngagement} icon="💬" color="green" />
        <StatCard title="Avg Views / Post" value={avgViews} icon="👁" color="blue" />
        <StatCard title="Avg Reach / Post" value={avgReach} icon="📡" color="purple" />
      </div>

      {/* Monthly Trend Chart */}
      {trendData.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Monthly Engagement Trend</h2>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tickFormatter={formatNumber} />
              <Tooltip
                formatter={(value, name) => [formatNumber(value), name.charAt(0).toUpperCase() + name.slice(1)]}
                labelFormatter={(label, payload) => {
                  if (payload?.[0]?.payload?.mom_change != null) {
                    const change = payload[0].payload.mom_change;
                    return `${label} (MoM: ${change > 0 ? '+' : ''}${change}%)`;
                  }
                  return label;
                }}
              />
              <Legend />
              <Bar dataKey="engagement" fill="#6366f1" name="Engagement" radius={[4, 4, 0, 0]} />
              <Bar dataKey="views" fill="#22c55e" name="Views" radius={[4, 4, 0, 0]} />
              <Bar dataKey="reach" fill="#f59e0b" name="Reach" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Month-over-Month Change Table */}
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
                {filteredMonthly.map((m, i) => (
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
                    <td className="text-right py-3 px-4">
                      {m.mom_change != null ? (
                        <span className={m.mom_change >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {m.mom_change > 0 ? '+' : ''}{m.mom_change}%
                        </span>
                      ) : (
                        <span className="text-gray-300">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Per-Page Breakdown for Selected Month */}
      {selectedMonth && (
        <>
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">
                Page Breakdown - {formatMonth(selectedMonth)}
              </h2>
              <select
                value={selectedMonth}
                onChange={(e) => setSelectedMonth(e.target.value)}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                {filteredMonthly.map(m => (
                  <option key={m.month} value={m.month}>{formatMonth(m.month)}</option>
                ))}
              </select>
            </div>

            {/* Page Comparison Bar Chart */}
            {pageComparisonData.length > 0 && (
              <ResponsiveContainer width="100%" height={Math.max(300, pageComparisonData.length * 35)}>
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

          {/* Per-Page Table */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Page Performance - {formatMonth(selectedMonth)}
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-500">#</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500">Page</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">Posts</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Reactions</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Comments</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Shares</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Engagement</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Views</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">Avg Reach</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500">MoM</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedMonthPages.map((p, i) => (
                    <tr key={p.page_id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4 text-gray-400">{i + 1}</td>
                      <td className="py-3 px-4 font-medium text-gray-900">{p.page_name}</td>
                      <td className="text-right py-3 px-4">{p.posts}</td>
                      <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.reactions / p.posts)) : 0}</td>
                      <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.comments / p.posts)) : 0}</td>
                      <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.shares / p.posts)) : 0}</td>
                      <td className="text-right py-3 px-4 font-semibold">{formatNumber(p.avg_engagement)}</td>
                      <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.views / p.posts)) : 0}</td>
                      <td className="text-right py-3 px-4">{p.posts > 0 ? formatNumber(Math.round(p.reach / p.posts)) : 0}</td>
                      <td className="text-right py-3 px-4">
                        {p.mom_change != null ? (
                          <span className={p.mom_change >= 0 ? 'text-green-600' : 'text-red-600'}>
                            {p.mom_change > 0 ? '+' : ''}{p.mom_change}%
                          </span>
                        ) : (
                          <span className="text-gray-300">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {selectedMonthPages.length === 0 && (
                <p className="text-center text-gray-400 py-8">No page data for this month</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
