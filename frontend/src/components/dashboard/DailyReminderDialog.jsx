import React from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  buildWhatsAppMessage,
  copyCustomerPhoneToClipboard,
  getCallUrl,
  getSmsUrl,
  getWhatsAppUrl,
} from '@/utils/renewalContact';

/**
 * The "policies expiring today" reminder modal.
 *
 * Open/close logic, snooze, and "mark notified" are handled by
 * ``useDailyReminder``; this component is purely presentational.
 */
const DailyReminderDialog = ({
  open,
  onOpenChange,
  onClose,
  rows,
  onMarkContacted,
}) => {
  const count = rows.length;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-2xl max-h-[90vh] flex flex-col gap-0 p-0 sm:max-w-2xl"
        data-testid="daily-reminder-dialog"
      >
        <div className="p-6 pb-2 pr-14">
          <DialogHeader>
            <DialogTitle>
              {count === 1 ? '1 policy expiring today' : `${count} policies expiring today`}
            </DialogTitle>
            <DialogDescription>
              Pre-filled renewal messages — use WhatsApp or SMS when a phone number is available.
            </DialogDescription>
          </DialogHeader>
        </div>
        <div className="px-6 flex-1 min-h-0 overflow-y-auto border-y bg-muted/30 max-h-[min(50vh,420px)]">
          <ul className="py-3 space-y-4">
            {rows.map((row) => {
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
                            void onMarkContacted(row);
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
                            void onMarkContacted(row);
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
              onClick={() => onClose('notified')}
              data-testid="daily-reminder-mark-notified"
            >
              Mark as notified
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => onClose('snooze')}
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
  );
};

export default DailyReminderDialog;
