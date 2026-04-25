import React from 'react';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import {
  CONTACT_STATUS,
  CONTACT_STATUS_OPTIONS,
  getEffectiveContactStatus,
  statusDisplayMeta,
} from '@/utils/contactStatus';
import {
  copyCustomerPhoneToClipboard,
  getCallUrl,
  getWhatsAppUrl,
} from '@/utils/renewalContact';
import { expiryRowContactClass, expiryRowUrgencyClass } from '@/utils/expiryStyles';

const TYPE_BADGE_BASE =
  'inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-xs font-medium text-[#5B21B6]';

const CHIP_BASE = 'h-8 rounded-full border px-3 text-xs font-medium transition-all duration-150 active:scale-[0.98]';
const CHIP_ACTIVE = 'border-[#2563EB] bg-[#2563EB] text-white';
const CHIP_IDLE = 'border-[#E5E7EB] bg-white text-[#334155] hover:bg-[#F8FAFC]';

/**
 * Counts + filter chips + expiry table — the "Expiring Soon" section.
 *
 * Pure UI: receives already-derived rows and counts plus the contact-action
 * callbacks. Owns no state of its own; the filter values live on the
 * parent so other components can react to them if needed later.
 */
const ExpiringSoonCard = ({
  expiringSoonRows,
  expiringCounts,
  filteredExpiringSoonRows,
  expiryInsuranceTypeOptions,
  contactFilter,
  onContactFilterChange,
  insuranceTypeFilter,
  onInsuranceTypeFilterChange,
  onMarkContacted,
  onContactStatusChange,
  onFollowUpDateChange,
}) => (
  <Card
    className="mb-3 rounded-2xl border border-[#E5E7EB] bg-gradient-to-br from-[#F5F3FF] to-[#EDE9FE] text-[#5B21B6] shadow-[0_2px_8px_rgba(15,23,42,0.06)] sm:mb-4"
    data-testid="expiring-soon-section"
  >
    <CardHeader className="p-4 pb-2 sm:p-5 sm:pb-2">
      <CardTitle className="text-base font-bold sm:text-lg">Expiring Soon</CardTitle>
      <CardDescription className="text-xs leading-relaxed text-[#64748B] sm:text-sm">
        Policies expiring in the next 7, 15, or 30 days (counts are cumulative — &quot;15 days&quot;
        includes all due on or before that window).
      </CardDescription>
    </CardHeader>
    <CardContent className="space-y-4 p-4 pt-2 sm:p-5 sm:pt-3">
      <div className="grid grid-cols-3 gap-2 sm:gap-3">
        <div
          className="rounded-xl border border-red-200/70 bg-white/70 px-2 py-3 text-center shadow-[0_2px_8px_rgba(15,23,42,0.04)]"
          data-testid="expiring-7d-count"
        >
          <p className="text-[11px] font-medium leading-tight text-[#64748B] sm:text-sm">7 days</p>
          <p className="mt-1 text-[22px] font-bold leading-tight tabular-nums text-[#DC2626] sm:text-[26px]">
            {expiringCounts.d7} <span aria-hidden="true">🔴</span>
          </p>
        </div>
        <div
          className="rounded-xl border border-orange-200/70 bg-white/70 px-2 py-3 text-center shadow-[0_2px_8px_rgba(15,23,42,0.04)]"
          data-testid="expiring-15d-count"
        >
          <p className="text-[11px] font-medium leading-tight text-[#64748B] sm:text-sm">15 days</p>
          <p className="mt-1 text-[22px] font-bold leading-tight tabular-nums text-[#F59E0B] sm:text-[26px]">
            {expiringCounts.d15} <span aria-hidden="true">🟠</span>
          </p>
        </div>
        <div
          className="rounded-xl border border-yellow-200/70 bg-white/70 px-2 py-3 text-center shadow-[0_2px_8px_rgba(15,23,42,0.04)]"
          data-testid="expiring-30d-count"
        >
          <p className="text-[11px] font-medium leading-tight text-[#64748B] sm:text-sm">30 days</p>
          <p className="mt-1 text-[22px] font-bold leading-tight tabular-nums text-[#5B21B6] sm:text-[26px]">
            {expiringCounts.d30} <span aria-hidden="true">🟡</span>
          </p>
        </div>
      </div>

      <div>
        <h3 className="mb-1 text-sm font-semibold text-[#0F172A]">Expiry list</h3>
        <p className="mb-3 text-xs text-[#64748B]">
          🔴 under 7 days · 🟠 under 15 days · 🟡 15–30 days · status tracks renewal outreach
        </p>
        <div className="flex flex-wrap items-end gap-3 mb-3">
          <div className="space-y-1">
            <Label htmlFor="expiry-contact-filter" className="text-xs font-medium text-[#64748B]">
              Contact filter
            </Label>
            <Select value={contactFilter} onValueChange={onContactFilterChange}>
              <SelectTrigger id="expiry-contact-filter" className="h-9 w-[220px] rounded-xl border-[#E5E7EB] bg-white">
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
          <div className="space-y-1">
            <Label className="text-xs font-medium text-[#64748B]">Insurance type</Label>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => onInsuranceTypeFilterChange('all')}
                data-testid="expiry-insurance-type-all"
                className={`${CHIP_BASE} ${insuranceTypeFilter === 'all' ? CHIP_ACTIVE : CHIP_IDLE}`}
              >
                All
              </button>
              {expiryInsuranceTypeOptions.map((opt) => (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => onInsuranceTypeFilterChange(opt.key)}
                  data-testid={`expiry-insurance-type-${opt.key}`}
                  className={`${CHIP_BASE} ${insuranceTypeFilter === opt.key ? CHIP_ACTIVE : CHIP_IDLE}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>
        </div>
        {expiringSoonRows.length === 0 ? (
          <p className="rounded-xl border border-[#E5E7EB] bg-white/70 py-6 text-center text-sm text-[#64748B]">
            No active policies expiring in the next 30 days.
          </p>
        ) : filteredExpiringSoonRows.length === 0 ? (
          <p className="rounded-xl border border-amber-200 bg-amber-50/80 py-6 text-center text-sm text-amber-900">
            No policies match this contact filter.
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-[#E5E7EB] bg-white">
            <Table>
              <TableHeader>
                <TableRow className="bg-[#F8FAFC]">
                  <TableHead className="min-w-[120px]">Customer</TableHead>
                  <TableHead className="min-w-[120px]">Insurance type</TableHead>
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
                  const urgency = row.daysLeft < 7 ? '🔴' : row.daysLeft < 15 ? '🟠' : '🟡';
                  const effective = getEffectiveContactStatus(row);
                  const meta = statusDisplayMeta(effective);
                  return (
                    <TableRow
                      key={row.policyId}
                      className={`${expiryRowUrgencyClass(row.daysLeft)} ${expiryRowContactClass(effective)}`}
                      data-testid={`expiry-row-${row.policyId}`}
                    >
                      <TableCell className="font-medium">{row.customerName}</TableCell>
                      <TableCell>
                        {row.insuranceType && row.insuranceType !== '—' ? (
                          <span className={TYPE_BADGE_BASE}>{row.insuranceType}</span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </TableCell>
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
                            value={effective}
                            onValueChange={(v) => void onContactStatusChange(row, v)}
                          >
                            <SelectTrigger
                              className="h-8 text-xs"
                              data-testid={`contact-status-${row.policyId}`}
                            >
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
                              <Label className="text-[10px] text-muted-foreground">
                                Follow-up date
                              </Label>
                              <Input
                                type="date"
                                className="h-8 text-xs"
                                value={
                                  row.follow_up_date
                                    ? String(row.follow_up_date).slice(0, 10)
                                    : ''
                                }
                                onChange={(e) =>
                                  void onFollowUpDateChange(row, e.target.value)
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
                                  void onMarkContacted(row);
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
                                  void onMarkContacted(row);
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
);

export default ExpiringSoonCard;
