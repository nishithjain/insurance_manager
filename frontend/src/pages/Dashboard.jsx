import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { policyAPI, customerAPI, syncAPI, importAPI } from '@/utils/api';
import {
  FileText,
  Users,
  AlertCircle,
  Pencil,
  Settings,
  Wallet,
  BarChart3,
} from 'lucide-react';
import AddInsuranceDialog from '@/components/AddInsuranceDialog';
import AddCustomerDialog from '@/components/AddCustomerDialog';
import EditPolicyDialog from '@/components/EditPolicyDialog';
import PendingPaymentsSection from '@/components/PendingPaymentsSection';
import UserMenu from '@/components/UserMenu';
import { isPendingPaymentStatus } from '@/utils/paymentStatus';
import {
  buildWhatsAppMessage,
  copyCustomerPhoneToClipboard,
  getCallUrl,
  getSmsUrl,
  getWhatsAppUrl,
  logRenewalContactDebug,
} from '@/utils/renewalContact';
import {
  buildPatchContactStatus,
  buildPatchMarkContacted,
  CONTACT_STATUS,
  CONTACT_STATUS_OPTIONS,
  defaultFollowUpDateYmd,
  getEffectiveContactStatus,
  statusDisplayMeta,
} from '@/utils/contactStatus';
import { isRenewalOpen } from '@/utils/renewalResolution';
import { daysLeftUntil, parsePolicyEndDate } from '@/utils/policyDates';

function formatLocalYMD(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function tomorrowYMD() {
  const t = new Date();
  t.setDate(t.getDate() + 1);
  return formatLocalYMD(t);
}

const LS_DAILY_REMINDER_NOTIFIED = 'insurance_daily_reminder_notified_date';
const LS_DAILY_REMINDER_SNOOZE = 'insurance_daily_reminder_snooze_until';

/** 🔴 &lt; 7 days, 🟠 &lt; 15 days, 🟡 within 30 days */
function expiryRowUrgencyClass(daysLeft) {
  if (daysLeft < 7) return 'border-l-4 border-red-500 bg-red-50/60';
  if (daysLeft < 15) return 'border-l-4 border-orange-400 bg-orange-50/60';
  return 'border-l-4 border-yellow-400 bg-yellow-50/50';
}

function expiryRowContactClass(effectiveStatus) {
  if (effectiveStatus === CONTACT_STATUS.FOLLOW_UP) {
    return 'ring-2 ring-inset ring-amber-400/90 bg-amber-50/50';
  }
  if (effectiveStatus === CONTACT_STATUS.CONTACTED_TODAY) {
    return 'opacity-[0.88]';
  }
  return 'font-semibold';
}

const Dashboard = () => {
  const [policies, setPolicies] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [syncStatus, setSyncStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statementRows, setStatementRows] = useState(null);
  const [editPolicy, setEditPolicy] = useState(null);
  const [dailyReminderOpen, setDailyReminderOpen] = useState(false);
  /** Expiry list: all | not_contacted | contacted_today | follow_up */
  const [expiryContactFilter, setExpiryContactFilter] = useState('all');
  /** One-shot auto-run: CSV only fills statement_policy_lines; customers need this materialize step. */
  const autoMaterializeAttempted = useRef(false);
  /** Avoid double-applying localStorage when Radix fires onOpenChange after programmatic close. */
  const dailyReminderCloseHandledRef = useRef(false);

  const refreshInsuranceData = () => Promise.all([loadPolicies(), loadCustomers()]);

  useEffect(() => {
    const init = async () => {
      try {
        await Promise.all([
          loadPolicies(),
          loadCustomers(),
          loadSyncStatus(),
          importAPI.statementSummary()
            .then((r) => setStatementRows(r.data.statement_rows))
            .catch(() => setStatementRows(null)),
        ]);
      } catch (error) {
        console.error('Failed to load:', error);
      } finally {
        setLoading(false);
      }
    };

    init();
  }, []);

  useEffect(() => {
    if (loading) return;
    if (statementRows === null || statementRows === 0) return;
    if (customers.length > 0 || policies.length > 0) return;
    if (autoMaterializeAttempted.current) return;
    autoMaterializeAttempted.current = true;
    let cancelled = false;
    (async () => {
      try {
        await importAPI.statementLinesToPolicies();
        if (cancelled) return;
        await Promise.all([loadPolicies(), loadCustomers()]);
        const s = await importAPI.statementSummary();
        setStatementRows(s.data.statement_rows);
      } catch (e) {
        console.error('Auto-import from statement CSV failed:', e);
        autoMaterializeAttempted.current = false;
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loading, statementRows, customers.length, policies.length]);

  const loadPolicies = async () => {
    try {
      const response = await policyAPI.getAll();
      setPolicies(response.data);
    } catch (error) {
      console.error('Failed to load policies:', error);
    }
  };

  const mergePolicyFromServer = useCallback((updated) => {
    setPolicies((prev) =>
      prev.map((p) => (String(p.id) === String(updated.id) ? { ...p, ...updated } : p))
    );
  }, []);

  const mergePolicyContactOptimistic = useCallback((policyId, partial) => {
    setPolicies((prev) =>
      prev.map((p) => (String(p.id) === String(policyId) ? { ...p, ...partial } : p))
    );
  }, []);

  const reloadPoliciesFromApi = async () => {
    try {
      const r = await policyAPI.getAll();
      setPolicies(r.data);
    } catch (e) {
      console.error(e);
    }
  };

  const markAsContactedForRow = useCallback(
    async (row) => {
      const patch = buildPatchMarkContacted();
      mergePolicyContactOptimistic(row.policyId, patch);
      try {
        const { data } = await policyAPI.patchContact(row.policyId, patch);
        mergePolicyFromServer(data);
      } catch (err) {
        console.error('Mark contacted failed:', err);
        await reloadPoliciesFromApi();
      }
    },
    [mergePolicyContactOptimistic, mergePolicyFromServer]
  );

  const handleContactStatusChange = useCallback(
    async (row, value) => {
      const ymd =
        value === CONTACT_STATUS.FOLLOW_UP
          ? row.follow_up_date || defaultFollowUpDateYmd()
          : null;
      const patch = buildPatchContactStatus(value, ymd);
      mergePolicyContactOptimistic(row.policyId, patch);
      try {
        const { data } = await policyAPI.patchContact(row.policyId, patch);
        mergePolicyFromServer(data);
      } catch (err) {
        console.error('Contact status update failed:', err);
        await reloadPoliciesFromApi();
      }
    },
    [mergePolicyContactOptimistic, mergePolicyFromServer]
  );

  const handleFollowUpDateChange = useCallback(
    async (row, ymd) => {
      if (!ymd) return;
      const patch = {
        contact_status: CONTACT_STATUS.FOLLOW_UP,
        follow_up_date: ymd,
        last_contacted_at: null,
      };
      mergePolicyContactOptimistic(row.policyId, patch);
      try {
        const { data } = await policyAPI.patchContact(row.policyId, patch);
        mergePolicyFromServer(data);
      } catch (err) {
        console.error('Follow-up date update failed:', err);
        await reloadPoliciesFromApi();
      }
    },
    [mergePolicyContactOptimistic, mergePolicyFromServer]
  );

  const loadCustomers = async () => {
    try {
      const response = await customerAPI.getAll();
      setCustomers(response.data);
    } catch (error) {
      console.error('Failed to load customers:', error);
    }
  };

  const loadSyncStatus = async () => {
    try {
      const response = await syncAPI.getStatus();
      setSyncStatus(response.data);
    } catch (error) {
      console.error('Failed to load sync status:', error);
    }
  };

  const activePolicies = policies.filter((p) => p.status === 'active');

  const pendingPaymentCount = useMemo(
    () => policies.filter((p) => isPendingPaymentStatus(p.payment_status)).length,
    [policies]
  );

  const customerNameForPolicy = (customerId) => {
    const c = customers.find((x) => String(x.id) === String(customerId));
    return c?.name?.trim() || '—';
  };

  const expiringSoonRows = useMemo(() => {
    const byId = Object.fromEntries(customers.map((c) => [String(c.id), c]));
    const rows = [];
    for (const p of policies) {
      if (p.status !== 'active') continue;
      const end = parsePolicyEndDate(p.end_date);
      if (!end) continue;
      const daysLeft = daysLeftUntil(end);
      if (daysLeft < 0 || daysLeft > 30) continue;
      const cust = byId[String(p.customer_id)];
      rows.push({
        policyId: p.id,
        customerName: cust?.name?.trim() || '—',
        phone: cust?.phone && String(cust.phone).trim() ? String(cust.phone).trim() : '',
        policyType: p.policy_type || '—',
        policyNumber: (p.policy_number && String(p.policy_number).trim()) || '—',
        endDate: end,
        daysLeft,
        last_contacted_at: p.last_contacted_at ?? null,
        contact_status: p.contact_status ?? CONTACT_STATUS.NOT_CONTACTED,
        follow_up_date: p.follow_up_date ?? null,
      });
    }
    rows.sort((a, b) => a.daysLeft - b.daysLeft);
    return rows;
  }, [policies, customers]);

  const expiringCounts = useMemo(
    () => ({
      d7: expiringSoonRows.filter((r) => r.daysLeft <= 7).length,
      d15: expiringSoonRows.filter((r) => r.daysLeft <= 15).length,
      d30: expiringSoonRows.length,
    }),
    [expiringSoonRows]
  );

  /** Missed-opportunities summary (detail page: /missed-opportunities). */
  const missedExpiredOpenCount = useMemo(() => {
    let n = 0;
    for (const p of policies) {
      if (p.status !== 'active') continue;
      const end = parsePolicyEndDate(p.end_date);
      if (!end) continue;
      if (daysLeftUntil(end) >= 0) continue;
      if (!isRenewalOpen(p)) continue;
      n += 1;
    }
    return n;
  }, [policies]);

  const expiringTodayRows = useMemo(
    () => expiringSoonRows.filter((r) => r.daysLeft === 0),
    [expiringSoonRows]
  );

  const filteredExpiringSoonRows = useMemo(() => {
    if (expiryContactFilter === 'all') return expiringSoonRows;
    return expiringSoonRows.filter((row) => {
      const eff = getEffectiveContactStatus(row);
      if (expiryContactFilter === 'not_contacted') return eff === CONTACT_STATUS.NOT_CONTACTED;
      if (expiryContactFilter === 'contacted_today') return eff === CONTACT_STATUS.CONTACTED_TODAY;
      if (expiryContactFilter === 'follow_up') return eff === CONTACT_STATUS.FOLLOW_UP;
      return true;
    });
  }, [expiringSoonRows, expiryContactFilter]);

  useEffect(() => {
    if (loading) return;
    if (expiringTodayRows.length === 0) {
      setDailyReminderOpen(false);
      return;
    }
    const todayStr = formatLocalYMD(new Date());
    if (localStorage.getItem(LS_DAILY_REMINDER_NOTIFIED) === todayStr) return;
    const snooze = localStorage.getItem(LS_DAILY_REMINDER_SNOOZE);
    if (snooze && todayStr < snooze) return;
    setDailyReminderOpen(true);
  }, [loading, expiringTodayRows]);

  useEffect(() => {
    if (!import.meta.env.DEV || expiringSoonRows.length === 0) return;
    logRenewalContactDebug(expiringSoonRows);
  }, [expiringSoonRows]);

  const closeDailyReminder = (kind) => {
    dailyReminderCloseHandledRef.current = true;
    const todayStr = formatLocalYMD(new Date());
    if (kind === 'notified') {
      localStorage.setItem(LS_DAILY_REMINDER_NOTIFIED, todayStr);
    } else {
      localStorage.setItem(LS_DAILY_REMINDER_SNOOZE, tomorrowYMD());
    }
    setDailyReminderOpen(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  const expiringTodayCount = expiringTodayRows.length;

  return (
    <div className="min-h-screen bg-gray-50">
      <Dialog
        open={dailyReminderOpen}
        onOpenChange={(open) => {
          if (open) {
            setDailyReminderOpen(true);
            return;
          }
          if (dailyReminderCloseHandledRef.current) {
            dailyReminderCloseHandledRef.current = false;
            return;
          }
          localStorage.setItem(LS_DAILY_REMINDER_SNOOZE, tomorrowYMD());
          setDailyReminderOpen(false);
        }}
      >
        <DialogContent
          className="max-w-2xl max-h-[90vh] flex flex-col gap-0 p-0 sm:max-w-2xl"
          data-testid="daily-reminder-dialog"
        >
          <div className="p-6 pb-2 pr-14">
            <DialogHeader>
              <DialogTitle>
                {expiringTodayCount === 1
                  ? '1 policy expiring today'
                  : `${expiringTodayCount} policies expiring today`}
              </DialogTitle>
              <DialogDescription>
                Pre-filled renewal messages — use WhatsApp or SMS when a phone number is available.
              </DialogDescription>
            </DialogHeader>
          </div>
          <div className="px-6 flex-1 min-h-0 overflow-y-auto border-y bg-muted/30 max-h-[min(50vh,420px)]">
            <ul className="py-3 space-y-4">
              {expiringTodayRows.map((row) => {
                const msg = buildWhatsAppMessage(row);
                const wa = getWhatsAppUrl(row);
                const sms = getSmsUrl(row);
                const callUrl = getCallUrl(row.phone);
                return (
                  <li
                    key={row.policyId}
                    className="rounded-lg border bg-background p-3 text-sm shadow-sm"
                    data-testid={`daily-reminder-policy-${row.policyId}`}
                  >
                    <div className="font-medium text-gray-900">{row.customerName}</div>
                    <div className="text-gray-600 mt-0.5">
                      {row.policyType} ·{' '}
                      {row.endDate.toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </div>
                    <p className="mt-2 text-xs text-gray-500 border-t pt-2 whitespace-pre-wrap">{msg}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {callUrl ? (
                        <Button variant="secondary" size="sm" asChild>
                          <a
                            href={callUrl}
                            title="Opens dialer and copies phone number"
                            onClick={() => {
                              void copyCustomerPhoneToClipboard(row.phone);
                              void markAsContactedForRow(row);
                            }}
                          >
                            <span aria-hidden="true">📞</span> Call
                          </a>
                        </Button>
                      ) : null}
                      {wa ? (
                        <Button variant="default" size="sm" asChild>
                          <a
                            href={wa}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={() => {
                              void markAsContactedForRow(row);
                            }}
                          >
                            <span aria-hidden="true">📱</span> WhatsApp ready
                          </a>
                        </Button>
                      ) : null}
                      {sms ? (
                        <Button variant="outline" size="sm" asChild>
                          <a href={sms}>
                            <span aria-hidden="true">📱</span> SMS ready
                          </a>
                        </Button>
                      ) : !callUrl && !wa ? (
                        <span className="text-xs text-amber-700">No phone on file — add in customer record</span>
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
          <DialogFooter className="p-6 pt-4 gap-2 sm:gap-2 flex-col sm:flex-row sm:justify-between">
            <div className="flex flex-wrap gap-2 w-full sm:w-auto">
              <Button
                type="button"
                variant="secondary"
                onClick={() => closeDailyReminder('notified')}
                data-testid="daily-reminder-mark-notified"
              >
                Mark as notified
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => closeDailyReminder('snooze')}
                data-testid="daily-reminder-snooze"
              >
                Snooze
              </Button>
            </div>
            <p className="text-xs text-muted-foreground w-full sm:text-right sm:max-w-xs">
              Snooze hides this until tomorrow. Mark as notified hides it for the rest of today.
            </p>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center gap-3">
              <img
                src="/InsuranceManager.png"
                alt=""
                className="w-10 h-10 rounded-lg object-cover shadow-sm"
              />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Insurance Manager</h1>
                <p className="text-sm text-gray-500">Local</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Link to="/statistics">
                <Button variant="outline" size="sm" data-testid="nav-statistics-btn">
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Statistics
                </Button>
              </Link>
              <Link to="/settings">
                <Button variant="outline" size="sm" data-testid="nav-settings-btn">
                  <Settings className="w-4 h-4 mr-2" />
                  Settings
                </Button>
              </Link>
              <Link to="/import-export">
                <Button variant="outline" size="sm" data-testid="nav-import-export-btn">
                  Import &amp; Export
                </Button>
              </Link>
              <Link to="/statements">
                <Button variant="outline" size="sm" data-testid="nav-statements-btn">
                  Statement CSV
                </Button>
              </Link>
              <UserMenu />
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Sync Status Alert */}
        {syncStatus &&
          (syncStatus.last_sync_time || syncStatus.sync_status) &&
          syncStatus.status !== 'never_synced' && (
          <Alert className="mb-6" data-testid="sync-status">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Last sync:{' '}
              {syncStatus.last_sync_time
                ? new Date(syncStatus.last_sync_time).toLocaleString()
                : 'Never'}{' '}
              — Status: {syncStatus.sync_status ?? syncStatus.status ?? '—'}
            </AlertDescription>
          </Alert>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card data-testid="total-policies-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Total Policies</p>
                  <p className="text-3xl font-bold text-gray-900">{policies.length}</p>
                </div>
                <FileText className="w-12 h-12 text-indigo-600 opacity-20" />
              </div>
            </CardContent>
          </Card>

          <Card data-testid="active-policies-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Active Policies</p>
                  <p className="text-3xl font-bold text-green-600">{activePolicies.length}</p>
                </div>
                <FileText className="w-12 h-12 text-green-600 opacity-20" />
              </div>
            </CardContent>
          </Card>

          <Card data-testid="customers-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Customers</p>
                  <p className="text-3xl font-bold text-blue-600">{customers.length}</p>
                </div>
                <Users className="w-12 h-12 text-blue-600 opacity-20" />
              </div>
            </CardContent>
          </Card>

          <Card data-testid="pending-payments-summary-card">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Pending payments</p>
                  <p className="text-3xl font-bold text-amber-600">{pendingPaymentCount}</p>
                </div>
                <Wallet className="w-12 h-12 text-amber-600 opacity-20" />
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="mb-8 shadow-sm" data-testid="missed-opportunities-section">
          <CardHeader>
            <CardTitle>Missed Opportunities</CardTitle>
            <CardDescription>
              Expired active policies with <strong>renewal status Open</strong>. Click the summary below
              to open the full resolution page (mix, table, notes).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex justify-center">
              <Link
                to="/missed-opportunities"
                className="group block w-full max-w-md rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2"
                data-testid="missed-expired-open-count-link"
              >
                <div
                  className="rounded-xl border-2 border-slate-300 bg-slate-50/90 px-6 py-5 text-center shadow-sm transition-colors group-hover:border-slate-400 group-hover:bg-slate-100/90"
                  data-testid="missed-expired-open-count"
                >
                  <p className="text-sm font-medium text-slate-900">
                    <span aria-hidden="true">❌</span> Expired but NOT Renewed
                  </p>
                  <p className="text-xs text-slate-600 mt-0.5">Expired (renewal open)</p>
                  <p className="mt-2 text-3xl font-bold tabular-nums text-slate-800">
                    {missedExpiredOpenCount} <span aria-hidden="true">❌</span>
                  </p>
                  <p className="mt-3 text-xs text-indigo-600 font-medium group-hover:underline">
                    Open resolution page →
                  </p>
                </div>
              </Link>
            </div>
          </CardContent>
        </Card>

        <PendingPaymentsSection
          policies={policies}
          customers={customers}
          onRefresh={refreshInsuranceData}
        />

        <Card className="mb-8 shadow-sm" data-testid="expiring-soon-section">
          <CardHeader>
            <CardTitle>Expiring Soon</CardTitle>
            <CardDescription>
              Policies expiring in the next 7, 15, or 30 days (counts are cumulative — &quot;15 days&quot;
              includes all due on or before that window).
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div
                className="rounded-xl border-2 border-red-200 bg-red-50/90 px-4 py-4 text-center shadow-sm"
                data-testid="expiring-7d-count"
              >
                <p className="text-sm font-medium text-red-900/90">Expiring in 7 days</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-red-800">
                  {expiringCounts.d7} <span aria-hidden="true">🔴</span>
                </p>
              </div>
              <div
                className="rounded-xl border-2 border-orange-200 bg-orange-50/90 px-4 py-4 text-center shadow-sm"
                data-testid="expiring-15d-count"
              >
                <p className="text-sm font-medium text-orange-900/90">Expiring in 15 days</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-orange-900">
                  {expiringCounts.d15} <span aria-hidden="true">🟠</span>
                </p>
              </div>
              <div
                className="rounded-xl border-2 border-yellow-200 bg-yellow-50/90 px-4 py-4 text-center shadow-sm"
                data-testid="expiring-30d-count"
              >
                <p className="text-sm font-medium text-yellow-900/90">Expiring in 30 days</p>
                <p className="mt-2 text-3xl font-bold tabular-nums text-yellow-900">
                  {expiringCounts.d30} <span aria-hidden="true">🟡</span>
                </p>
              </div>
            </div>

            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-1">Expiry list</h3>
              <p className="text-xs text-gray-500 mb-3">
                🔴 under 7 days · 🟠 under 15 days · 🟡 15–30 days · status tracks renewal outreach
              </p>
              <div className="flex flex-wrap items-end gap-3 mb-3">
                <div className="space-y-1">
                  <Label htmlFor="expiry-contact-filter" className="text-xs text-gray-600">
                    Contact filter
                  </Label>
                  <Select value={expiryContactFilter} onValueChange={setExpiryContactFilter}>
                    <SelectTrigger id="expiry-contact-filter" className="w-[220px] h-9">
                      <SelectValue placeholder="All" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All</SelectItem>
                      <SelectItem value="not_contacted">Not Contacted</SelectItem>
                      <SelectItem value="contacted_today">Contacted Today</SelectItem>
                      <SelectItem value="follow_up">Follow-up Needed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {expiringSoonRows.length === 0 ? (
                <p className="text-sm text-gray-500 py-6 text-center border rounded-lg bg-gray-50/80">
                  No active policies expiring in the next 30 days.
                </p>
              ) : filteredExpiringSoonRows.length === 0 ? (
                <p className="text-sm text-amber-900 py-6 text-center border border-amber-200 rounded-lg bg-amber-50/80">
                  No policies match this contact filter.
                </p>
              ) : (
                <div className="rounded-lg border bg-white overflow-hidden">
                  <Table>
                    <TableHeader>
                      <TableRow className="bg-gray-50/80">
                        <TableHead className="min-w-[120px]">Customer</TableHead>
                        <TableHead>Policy type</TableHead>
                        <TableHead>Expiry date</TableHead>
                        <TableHead>Days left</TableHead>
                        <TableHead className="min-w-[200px]">Status</TableHead>
                        <TableHead className="min-w-[180px]">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredExpiringSoonRows.map((row) => {
                        const callUrl = getCallUrl(row.phone);
                        const waUrl = getWhatsAppUrl(row);
                        const expiryLabel = row.endDate.toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                        });
                        const urgency =
                          row.daysLeft < 7 ? '🔴' : row.daysLeft < 15 ? '🟠' : '🟡';
                        const effective = getEffectiveContactStatus(row);
                        const meta = statusDisplayMeta(effective);
                        const statusSelectValue = effective;
                        return (
                          <TableRow
                            key={row.policyId}
                            className={`${expiryRowUrgencyClass(row.daysLeft)} ${expiryRowContactClass(effective)}`}
                            data-testid={`expiry-row-${row.policyId}`}
                          >
                            <TableCell className="font-medium">{row.customerName}</TableCell>
                            <TableCell>{row.policyType}</TableCell>
                            <TableCell className="whitespace-nowrap">{expiryLabel}</TableCell>
                            <TableCell>
                              <span className="mr-1.5" aria-hidden="true">
                                {urgency}
                              </span>
                              {row.daysLeft} {row.daysLeft === 1 ? 'day' : 'days'}
                            </TableCell>
                            <TableCell className="align-top min-w-[200px]">
                              <div className="space-y-2 max-w-[240px]">
                                <div className="text-sm">
                                  <span aria-hidden="true">{meta.emoji}</span>{' '}
                                  <span className="font-medium">{meta.label}</span>
                                </div>
                                <Select
                                  value={statusSelectValue}
                                  onValueChange={(v) => void handleContactStatusChange(row, v)}
                                >
                                  <SelectTrigger className="h-8 text-xs" data-testid={`contact-status-${row.policyId}`}>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {CONTACT_STATUS_OPTIONS.map((opt) => (
                                      <SelectItem key={opt} value={opt}>
                                        {opt}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                                {effective === CONTACT_STATUS.FOLLOW_UP ? (
                                  <div className="space-y-0.5">
                                    <Label className="text-[10px] text-muted-foreground">Follow-up date</Label>
                                    <Input
                                      type="date"
                                      className="h-8 text-xs"
                                      value={
                                        row.follow_up_date
                                          ? String(row.follow_up_date).slice(0, 10)
                                          : ''
                                      }
                                      onChange={(e) =>
                                        void handleFollowUpDateChange(row, e.target.value)
                                      }
                                    />
                                  </div>
                                ) : null}
                              </div>
                            </TableCell>
                            <TableCell>
                              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                                {callUrl && waUrl ? (
                                  <>
                                    <a
                                      href={callUrl}
                                      className="text-indigo-700 hover:underline font-medium"
                                      title="Opens dialer and copies phone number"
                                      onClick={() => {
                                        void copyCustomerPhoneToClipboard(row.phone);
                                        void markAsContactedForRow(row);
                                      }}
                                    >
                                      📞 Call
                                    </a>
                                    <a
                                      href={waUrl}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      className="text-green-700 hover:underline font-medium"
                                      onClick={() => {
                                        void markAsContactedForRow(row);
                                      }}
                                    >
                                      WhatsApp
                                    </a>
                                  </>
                                ) : (
                                  <span className="text-gray-600">No phone on file</span>
                                )}
                              </div>
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 gap-6">
          <Card data-testid="recent-policies">
            <CardHeader>
              <div className="flex flex-wrap justify-between items-center gap-2">
                <CardTitle>Recent Policies</CardTitle>
                <div className="flex flex-wrap gap-2">
                  <AddInsuranceDialog
                    customers={customers}
                    policies={policies}
                    onSuccess={refreshInsuranceData}
                  />
                  <AddCustomerDialog onSuccess={() => refreshInsuranceData()} />
                </div>
              </div>
              <CardDescription className="text-xs pt-1">
                Add a customer or policy, or edit a row below.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {policies.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No policies yet</p>
              ) : (
                <div className="space-y-3">
                  {policies.slice(0, 5).map((policy) => (
                    <div
                      key={policy.id}
                      className="flex justify-between items-start gap-3 p-3 bg-gray-50 rounded-lg"
                    >
                      <div className="min-w-0 flex-1 space-y-2">
                        <p className="text-base text-gray-900 break-words">
                          <span className="text-gray-500">Customer name: </span>
                          <span className="font-semibold text-gray-900">
                            {customerNameForPolicy(policy.customer_id)}
                          </span>
                        </p>
                        <div className="text-sm text-gray-700 space-y-0.5">
                          <p className="truncate">
                            <span className="text-gray-500">Policy number: </span>
                            {policy.policy_number || '—'}
                          </p>
                          <p className="truncate">
                            <span className="text-gray-500">Policy type: </span>
                            {policy.policy_type || '—'}
                          </p>
                          <p className="truncate">
                            <span className="text-gray-500">Company: </span>
                            {policy.insurer_company && String(policy.insurer_company).trim()
                              ? policy.insurer_company
                              : '—'}
                          </p>
                          <p className="flex flex-wrap items-center gap-1.5">
                            <span className="text-gray-500">Active: </span>
                            <Badge variant={policy.status === 'active' ? 'default' : 'secondary'}>
                              {policy.status}
                            </Badge>
                          </p>
                        </div>
                      </div>
                      <div className="flex items-start gap-1 shrink-0 pt-1">
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => setEditPolicy(policy)}
                          aria-label="Edit policy"
                          data-testid={`edit-policy-${policy.id}`}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <EditPolicyDialog
          policy={editPolicy}
          customers={customers}
          open={!!editPolicy}
          onOpenChange={(o) => {
            if (!o) setEditPolicy(null);
          }}
          onSuccess={refreshInsuranceData}
        />
      </div>
    </div>
  );
};

export default Dashboard;
