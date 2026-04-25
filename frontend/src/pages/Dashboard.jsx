import React, { useEffect, useMemo, useState } from 'react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import EditPolicyDialog from '@/components/EditPolicyDialog';
import PendingPaymentsSection from '@/components/PendingPaymentsSection';
import DailyReminderDialog from '@/components/dashboard/DailyReminderDialog';
import DashboardHeader from '@/components/dashboard/DashboardHeader';
import DashboardStatsCards from '@/components/dashboard/DashboardStatsCards';
import ExpiringSoonCard from '@/components/dashboard/ExpiringSoonCard';
import MissedOpportunitiesCard from '@/components/dashboard/MissedOpportunitiesCard';
import RecentPoliciesCard from '@/components/dashboard/RecentPoliciesCard';
import { useDailyReminder } from '@/hooks/useDailyReminder';
import { useDashboardContactActions } from '@/hooks/useDashboardContactActions';
import { useDashboardData } from '@/hooks/useDashboardData';
import { useExpiringPolicies } from '@/hooks/useExpiringPolicies';
import { isPendingPaymentStatus } from '@/utils/paymentStatus';
import { logRenewalContactDebug } from '@/utils/renewalContact';

/**
 * Top-level dashboard page.
 *
 * The page itself is intentionally thin — its only jobs are:
 *
 *   1. Wire the data-loading hook to the contact-action hook to the
 *      derived-selectors hook, so each presentational sub-component
 *      receives exactly what it needs;
 *   2. Compose the page layout (header + sections);
 *   3. Manage two pieces of *local* UI state — the expiry filters and
 *      the currently-edited policy — that are not shared.
 */
const Dashboard = () => {
  const {
    policies,
    setPolicies,
    customers,
    syncStatus,
    loading,
    refreshInsuranceData,
  } = useDashboardData();

  const { markAsContactedForRow, handleContactStatusChange, handleFollowUpDateChange } =
    useDashboardContactActions(setPolicies);

  /** Expiry list: all | not_contacted | contacted_today | follow_up. */
  const [expiryContactFilter, setExpiryContactFilter] = useState('all');
  /** Expiry list insurance-type filter: 'all' | <insurance_type_name lowercased>. */
  const [expiryInsuranceTypeFilter, setExpiryInsuranceTypeFilter] = useState('all');
  const [editPolicy, setEditPolicy] = useState(null);

  const {
    expiringSoonRows,
    expiringCounts,
    expiringTodayRows,
    expiryInsuranceTypeOptions,
    filteredExpiringSoonRows,
    missedExpiredOpenCount,
  } = useExpiringPolicies(policies, customers, expiryContactFilter, expiryInsuranceTypeFilter);

  const dailyReminder = useDailyReminder({ loading, expiringTodayRows });

  const activePolicies = useMemo(
    () => policies.filter((p) => p.status === 'active'),
    [policies]
  );
  const pendingPaymentCount = useMemo(
    () => policies.filter((p) => isPendingPaymentStatus(p.payment_status)).length,
    [policies]
  );

  useEffect(() => {
    if (!import.meta.env.DEV || expiringSoonRows.length === 0) return;
    logRenewalContactDebug(expiringSoonRows);
  }, [expiringSoonRows]);

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

  const showSyncBanner =
    syncStatus &&
    (syncStatus.last_sync_time || syncStatus.sync_status) &&
    syncStatus.status !== 'never_synced';

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#0F172A]">
      <DailyReminderDialog
        open={dailyReminder.open}
        onOpenChange={dailyReminder.onOpenChange}
        onClose={dailyReminder.close}
        rows={expiringTodayRows}
        onMarkContacted={markAsContactedForRow}
      />

      <DashboardHeader />

      <div className="mx-auto max-w-7xl px-[14px] py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8">
        {showSyncBanner && (
          <Alert
            className="mb-3 rounded-2xl border-[#E5E7EB] bg-white shadow-[0_2px_8px_rgba(15,23,42,0.06)] sm:mb-4"
            data-testid="sync-status"
          >
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

        <DashboardStatsCards
          totalPolicies={policies.length}
          activePolicies={activePolicies.length}
          customers={customers.length}
          pendingPaymentCount={pendingPaymentCount}
        />

        <MissedOpportunitiesCard count={missedExpiredOpenCount} />

        <PendingPaymentsSection
          policies={policies}
          customers={customers}
          onRefresh={refreshInsuranceData}
        />

        <ExpiringSoonCard
          expiringSoonRows={expiringSoonRows}
          expiringCounts={expiringCounts}
          filteredExpiringSoonRows={filteredExpiringSoonRows}
          expiryInsuranceTypeOptions={expiryInsuranceTypeOptions}
          contactFilter={expiryContactFilter}
          onContactFilterChange={setExpiryContactFilter}
          insuranceTypeFilter={expiryInsuranceTypeFilter}
          onInsuranceTypeFilterChange={setExpiryInsuranceTypeFilter}
          onMarkContacted={markAsContactedForRow}
          onContactStatusChange={handleContactStatusChange}
          onFollowUpDateChange={handleFollowUpDateChange}
        />

        <div className="grid grid-cols-1 gap-3 sm:gap-4">
          <RecentPoliciesCard
            policies={policies}
            customers={customers}
            onRefresh={refreshInsuranceData}
            onEditPolicy={setEditPolicy}
          />
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
