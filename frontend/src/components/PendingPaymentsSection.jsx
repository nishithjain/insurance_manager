import React, { useMemo, useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import UpdatePaymentDialog from '@/components/UpdatePaymentDialog';
import {
  getPendingPaymentRows,
  filterPendingRowsBySearch,
  sortPendingRows,
  summarizePendingPayments,
  isUrgentExpiry,
} from '@/utils/pendingPayments';
import { getPaymentStatusBadgeClass } from '@/utils/paymentStatus';
import { Wallet } from 'lucide-react';

/**
 * @param {{ policies: object[], customers: object[], onRefresh: () => Promise<void>|void }} props
 */
const PendingPaymentsSection = ({ policies, customers, onRefresh }) => {
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('expiry_asc');
  const [dialogPolicy, setDialogPolicy] = useState(null);

  const customersById = useMemo(
    () => Object.fromEntries((customers || []).map((c) => [String(c.id), c])),
    [customers]
  );

  const pendingRows = useMemo(
    () => getPendingPaymentRows(policies, customersById),
    [policies, customersById]
  );

  const filtered = useMemo(
    () => filterPendingRowsBySearch(pendingRows, search),
    [pendingRows, search]
  );

  const sorted = useMemo(() => sortPendingRows(filtered, sortBy), [filtered, sortBy]);

  const summary = useMemo(() => summarizePendingPayments(pendingRows), [pendingRows]);

  const handlePaymentSuccess = async () => {
    await onRefresh?.();
  };

  return (
    <>
      <Card
        className="mb-3 rounded-2xl border border-[#E5E7EB] bg-white shadow-[0_2px_8px_rgba(15,23,42,0.06)] sm:mb-4"
        data-testid="pending-payments-section"
      >
        <CardHeader className="p-4 pb-2 sm:p-5 sm:pb-2">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2 text-base font-bold text-[#0F172A] sm:text-lg">
                <Wallet className="h-5 w-5 text-[#F59E0B] stroke-[2]" aria-hidden />
                Pending Payments
              </CardTitle>
              <CardDescription className="pt-1 text-xs leading-relaxed text-[#64748B] sm:text-sm">
                Policies with payment status <strong>PENDING</strong>. Update when payment is received —
                the row leaves this list immediately after you save (data is stored on the server).
              </CardDescription>
            </div>
            <div className="grid w-full grid-cols-2 gap-2 text-sm sm:w-auto">
              <div className="rounded-xl border border-orange-200/70 bg-gradient-to-br from-[#FFF7ED] to-[#FFEDD5] px-3 py-2 text-[#9A3412]">
                <span className="text-xs font-medium text-[#9A3412]/80">Pending count</span>
                <p className="text-[24px] font-bold leading-tight tabular-nums sm:text-[26px]">{summary.count}</p>
              </div>
              <div className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] px-3 py-2 text-[#0F172A]">
                <span className="text-xs font-medium text-[#64748B]">Premium total</span>
                <p className="text-[24px] font-bold leading-tight tabular-nums sm:text-[26px]">
                  ₹
                  {summary.totalPremium.toLocaleString('en-IN', {
                    minimumFractionDigits: 0,
                    maximumFractionDigits: 2,
                  })}
                </p>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 p-4 pt-2 sm:p-5 sm:pt-3">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[200px] flex-1 space-y-1">
              <Label htmlFor="pending-pay-search" className="text-xs font-medium text-[#64748B]">Search</Label>
              <Input
                id="pending-pay-search"
                placeholder="Customer name, insurance type, policy type, phone…"
                className="h-10 rounded-xl border-[#E5E7EB] bg-[#F8FAFC]"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="w-full space-y-1 sm:w-[200px]">
              <Label htmlFor="pending-pay-sort" className="text-xs font-medium text-[#64748B]">Sort by</Label>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger id="pending-pay-sort" className="h-10 rounded-xl border-[#E5E7EB] bg-[#F8FAFC]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="expiry_asc">Expiry date (soonest first)</SelectItem>
                  <SelectItem value="name_asc">Customer name (A–Z)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {sorted.length === 0 ? (
            <p className="rounded-xl border border-[#E5E7EB] bg-[#F8FAFC] py-6 text-center text-sm text-[#64748B]">
              {pendingRows.length === 0
                ? 'No policies with PENDING payment status.'
                : 'No rows match your search.'}
            </p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-[#E5E7EB] bg-white">
              <Table>
                <TableHeader>
                  <TableRow className="bg-[#F8FAFC]">
                    <TableHead>Customer</TableHead>
                    <TableHead>Insurance type</TableHead>
                    <TableHead>Policy type</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead className="text-right">Premium</TableHead>
                    <TableHead>Payment status</TableHead>
                    <TableHead>Expiry</TableHead>
                    <TableHead className="w-[140px]">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sorted.map((row) => {
                    const urgent = isUrgentExpiry(row.daysLeft, 7);
                    const exp = row.endDate
                      ? row.endDate.toLocaleDateString('en-IN', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })
                      : '—';
                    const prem = row.policy.premium;
                    const premStr =
                      prem == null || prem === ''
                        ? '—'
                        : `₹${Number(prem).toLocaleString('en-IN', {
                            minimumFractionDigits: 0,
                            maximumFractionDigits: 2,
                          })}`;
                    return (
                      <TableRow
                        key={row.policy.id}
                        className={
                          urgent
                            ? 'bg-red-50/70 border-l-2 border-l-[#DC2626]'
                            : 'border-l-2 border-l-transparent'
                        }
                      >
                        <TableCell className="font-medium">{row.customerName}</TableCell>
                        <TableCell>{row.policy.insurance_type_name || '—'}</TableCell>
                        <TableCell>{row.policy.policy_type_name || row.policy.policy_type || '—'}</TableCell>
                        <TableCell className="text-sm">{row.phone || '—'}</TableCell>
                        <TableCell className="text-right tabular-nums">{premStr}</TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={`whitespace-normal font-normal ${getPaymentStatusBadgeClass(
                              row.policy.payment_status
                            )}`}
                          >
                            {row.policy.payment_status || 'PENDING'}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm">{exp}</span>
                          {row.daysLeft != null && row.daysLeft >= 0 && (
                            <span className="block text-xs text-muted-foreground">
                              {row.daysLeft === 0
                                ? 'Today'
                                : `${row.daysLeft} day${row.daysLeft === 1 ? '' : 's'} left`}
                            </span>
                          )}
                        </TableCell>
                        <TableCell>
                          <Button
                            type="button"
                            size="sm"
                            variant="default"
                            className="rounded-xl bg-[#2563EB] transition-all duration-150 active:scale-[0.98]"
                            onClick={() => setDialogPolicy(row.policy)}
                          >
                            Update payment
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <UpdatePaymentDialog
        policy={dialogPolicy}
        open={!!dialogPolicy}
        onOpenChange={(o) => {
          if (!o) setDialogPolicy(null);
        }}
        onSuccess={async () => {
          setDialogPolicy(null);
          await handlePaymentSuccess();
        }}
      />
    </>
  );
};

export default PendingPaymentsSection;
