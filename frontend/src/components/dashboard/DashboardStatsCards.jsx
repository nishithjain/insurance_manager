import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { FileText, Users, Wallet } from 'lucide-react';

const statCardClass =
  'rounded-2xl border border-[#E5E7EB] bg-white shadow-[0_2px_8px_rgba(15,23,42,0.06)] transition-all duration-150 active:scale-[0.98]';

const iconWrapClass = 'flex h-9 w-9 items-center justify-center rounded-xl sm:h-10 sm:w-10';

/** Four headline metrics shown above the dashboard sections. */
const DashboardStatsCards = ({
  totalPolicies,
  activePolicies,
  customers,
  pendingPaymentCount,
}) => (
  <div className="mb-3 grid grid-cols-2 gap-3 sm:mb-4 md:grid-cols-2 lg:grid-cols-4">
    <Card className={statCardClass} data-testid="total-policies-card">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-xs font-medium text-[#64748B]">Total Policies</p>
            <p className="text-[24px] font-bold leading-tight tabular-nums text-[#0F172A] sm:text-[26px]">
              {totalPolicies}
            </p>
          </div>
          <span className={`${iconWrapClass} bg-[#EFF6FF] text-[#2563EB]`}>
            <FileText className="h-5 w-5 stroke-[2]" />
          </span>
        </div>
      </CardContent>
    </Card>

    <Card className={statCardClass} data-testid="active-policies-card">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-xs font-medium text-[#64748B]">Active Policies</p>
            <p className="text-[24px] font-bold leading-tight tabular-nums text-[#16A34A] sm:text-[26px]">
              {activePolicies}
            </p>
          </div>
          <span className={`${iconWrapClass} bg-[#F0FDF4] text-[#16A34A]`}>
            <FileText className="h-5 w-5 stroke-[2]" />
          </span>
        </div>
      </CardContent>
    </Card>

    <Card className={statCardClass} data-testid="customers-card">
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-xs font-medium text-[#64748B]">Customers</p>
            <p className="text-[24px] font-bold leading-tight tabular-nums text-[#2563EB] sm:text-[26px]">
              {customers}
            </p>
          </div>
          <span className={`${iconWrapClass} bg-[#EFF6FF] text-[#2563EB]`}>
            <Users className="h-5 w-5 stroke-[2]" />
          </span>
        </div>
      </CardContent>
    </Card>

    <Card
      className={`${statCardClass} bg-gradient-to-br from-[#FFF7ED] to-[#FFEDD5]`}
      data-testid="pending-payments-summary-card"
    >
      <CardContent className="p-3 sm:p-4">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <p className="text-xs font-medium text-[#9A3412]/80">Pending payments</p>
            <p className="text-[24px] font-bold leading-tight tabular-nums text-[#9A3412] sm:text-[26px]">
              {pendingPaymentCount}
            </p>
          </div>
          <span className={`${iconWrapClass} bg-white/60 text-[#F59E0B]`}>
            <Wallet className="h-5 w-5 stroke-[2]" />
          </span>
        </div>
      </CardContent>
    </Card>
  </div>
);

export default DashboardStatsCards;
