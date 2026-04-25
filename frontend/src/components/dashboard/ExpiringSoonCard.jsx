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
  'inline-flex items-center rounded-full border border-indigo-200 bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-800';

const CHIP_BASE = 'h-8 rounded-full border px-3 text-xs font-medium transition-colors';
const CHIP_ACTIVE = 'border-indigo-600 bg-indigo-600 text-white';
const CHIP_IDLE = 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50';

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
            <Select value={contactFilter} onValueChange={onContactFilterChange}>
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
          <div className="space-y-1">
            <Label className="text-xs text-gray-600">Insurance type</Label>
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
