import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { statisticsAPI } from '@/utils/api';
import {
  ArrowLeft,
  BarChart3,
  IndianRupee,
  Users,
  RefreshCw,
  AlertTriangle,
  PieChart as PieChartIcon,
} from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const PIE_COLORS = ['#4f46e5', '#059669', '#d97706', '#dc2626', '#7c3aed', '#0ea5e9', '#64748b'];

function formatInr(n) {
  if (n == null || Number.isNaN(Number(n))) return '—';
  return `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

function pctLabel(rate) {
  if (rate == null) return '—';
  return `${(Number(rate) * 100).toFixed(1)}%`;
}

const Statistics = () => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const run = async () => {
      try {
        const res = await statisticsAPI.getDashboard();
        setData(res.data);
      } catch (e) {
        console.error(e);
        setError(e.response?.data?.detail || e.message || 'Failed to load statistics');
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <p className="text-gray-600">Loading statistics…</p>
      </div>
    );
  }

  const trend = data?.monthly_trend || [];
  const pieData = (data?.policy_type_distribution || []).map((d) => ({
    name: d.policy_type,
    value: d.count,
  }));

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center gap-4">
              <Link to="/dashboard">
                <Button variant="outline" size="sm">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Dashboard
                </Button>
              </Link>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-6 h-6 text-indigo-600" />
                <div>
                  <h1 className="text-lg font-semibold text-gray-900">Statistics</h1>
                  <p className="text-sm text-gray-500">
                    Month {data?.current_month_label} · As of {data?.as_of_date}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900">
            {error}
          </div>
        )}

        {/* Payments */}
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Payment performance
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Received this month</CardDescription>
                <CardTitle className="text-2xl tabular-nums text-emerald-700">
                  {formatInr(data?.payment_received_this_month)}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                Sum of premiums (non-PENDING) with activity in the current calendar month.
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Pending count</CardDescription>
                <CardTitle className="text-2xl tabular-nums text-amber-700">
                  {data?.pending_payments_count ?? '—'}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex items-center gap-2 text-xs text-muted-foreground">
                <IndianRupee className="h-4 w-4" />
                Pending amount:{' '}
                <span className="font-semibold text-foreground">
                  {formatInr(data?.pending_payments_amount)}
                </span>
              </CardContent>
            </Card>
            <Card className="border-dashed">
              <CardHeader className="pb-2">
                <CardDescription>Definitions</CardDescription>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground leading-relaxed">
                <strong>Received</strong> uses payment status ≠ PENDING and dates from{' '}
                <code className="text-[11px]">payment_updated_at</code> (or{' '}
                <code className="text-[11px]">updated_at</code>).
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Renewals & expiry */}
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Renewals &amp; expiry
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1">
                  <RefreshCw className="h-3.5 w-3.5" />
                  Renewals this month
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">{data?.renewals_this_month ?? '—'}</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                Resolved as RenewedWithUs / RenewedElsewhere (by resolution date).
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Expiring this month</CardDescription>
                <CardTitle className="text-2xl tabular-nums">{data?.expiring_this_month ?? '—'}</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                Active policies with end date in this calendar month.
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Renewal conversion (month)</CardDescription>
                <CardTitle className="text-2xl tabular-nums text-indigo-700">
                  {pctLabel(data?.renewal_conversion_rate)}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                renewals ÷ expiring (same month). Shows — if no expiries.
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1 text-amber-900">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Expired, not renewed
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums text-amber-900">
                  {data?.expired_not_renewed_open ?? '—'}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                Active, past <code className="text-[11px]">policy_end_date</code>, renewal still Open.
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Portfolio: customers + policies */}
        <div>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Portfolio</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-4xl">
            <Card>
              <CardHeader className="pb-2">
                <CardDescription className="flex items-center gap-1">
                  <Users className="h-3.5 w-3.5" />
                  Total customers
                </CardDescription>
                <CardTitle className="text-2xl tabular-nums">{data?.total_customers ?? '—'}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Total policies</CardDescription>
                <CardTitle className="text-2xl tabular-nums">{data?.total_policies ?? '—'}</CardTitle>
              </CardHeader>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardDescription>Repeat customers</CardDescription>
                <CardTitle className="text-2xl tabular-nums text-blue-700">
                  {data?.repeat_customers ?? '—'}
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground">
                Customers with more than one policy.
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Last 6 months</CardTitle>
              <CardDescription>Payments received, renewals resolved, and policies expiring per month</CardDescription>
            </CardHeader>
            <CardContent className="h-[320px]">
              {trend.length === 0 ? (
                <p className="text-sm text-muted-foreground">No trend data.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trend} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                    <Tooltip
                      formatter={(value, name) => [
                        String(name).includes('Payments') ? formatInr(value) : value,
                        name,
                      ]}
                    />
                    <Legend />
                    <Bar dataKey="payments_received" name="Payments (₹)" fill="#059669" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="renewals" name="Renewals" fill="#4f46e5" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="expiring" name="Expiring" fill="#d97706" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <PieChartIcon className="h-5 w-5 text-indigo-600" />
                Policy type mix
              </CardTitle>
              <CardDescription>All policies for your account</CardDescription>
            </CardHeader>
            <CardContent className="h-[320px]">
              {pieData.length === 0 ? (
                <p className="text-sm text-muted-foreground">No policies to chart.</p>
              ) : (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={100}
                      label={({ name, percent }) =>
                        `${name || ''} ${percent != null ? (percent * 100).toFixed(0) : 0}%`
                      }
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={`${entry.name}-${i}`} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(v) => [v, 'Policies']} />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Statistics;
