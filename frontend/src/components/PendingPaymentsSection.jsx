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
      <Card className="mb-8 shadow-sm" data-testid="pending-payments-section">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Wallet className="h-5 w-5 text-amber-600" aria-hidden />
                Pending Payments
              </CardTitle>
              <CardDescription className="pt-1">
                Policies with payment status <strong>PENDING</strong>. Update when payment is received —
                the row leaves this list immediately after you save (data is stored on the server).
              </CardDescription>
            </div>
            <div className="flex flex-wrap gap-3 text-sm">
              <div className="rounded-lg border bg-amber-50/80 px-3 py-2 text-amber-950">
                <span className="text-amber-800/90">Pending count</span>
                <p className="text-2xl font-bold tabular-nums">{summary.count}</p>
              </div>
              <div className="rounded-lg border bg-slate-50 px-3 py-2 text-slate-900">
                <span className="text-slate-600">Pending premium total</span>
                <p className="text-2xl font-bold tabular-nums">
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
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-1 flex-1 min-w-[200px]">
              <Label htmlFor="pending-pay-search">Search</Label>
              <Input
                id="pending-pay-search"
                placeholder="Customer name, policy number, phone…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="space-y-1 w-[200px]">
              <Label htmlFor="pending-pay-sort">Sort by</Label>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger id="pending-pay-sort">
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
            <p className="text-sm text-muted-foreground py-8 text-center border rounded-lg bg-muted/20">
              {pendingRows.length === 0
                ? 'No policies with PENDING payment status.'
                : 'No rows match your search.'}
            </p>
          ) : (
            <div className="rounded-lg border bg-white overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-muted/50">
                    <TableHead>Customer</TableHead>
                    <TableHead>Policy type</TableHead>
                    <TableHead>Policy number</TableHead>
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
                            ? 'bg-red-50/70 border-l-4 border-l-red-500'
                            : 'border-l-4 border-l-transparent'
                        }
                      >
                        <TableCell className="font-medium">{row.customerName}</TableCell>
                        <TableCell>{row.policy.policy_type || '—'}</TableCell>
                        <TableCell className="font-mono text-sm">{row.policy.policy_number || '—'}</TableCell>
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
