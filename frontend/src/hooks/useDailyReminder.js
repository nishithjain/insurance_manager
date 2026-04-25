import { useEffect, useRef, useState } from 'react';
import { formatLocalYMD, tomorrowYMD } from '@/utils/policyDates';

const LS_DAILY_REMINDER_NOTIFIED = 'insurance_daily_reminder_notified_date';
const LS_DAILY_REMINDER_SNOOZE = 'insurance_daily_reminder_snooze_until';

/**
 * Drives the once-per-day "policies expiring today" reminder dialog.
 *
 * Auto-opens at most once per local day. Uses two localStorage keys to
 * remember whether the user marked "notified" (suppresses for the rest
 * of the day) or "snoozed" (suppresses until tomorrow). The Radix
 * onOpenChange handler is bridged through a ref so a programmatic close
 * does not re-snooze.
 */
export function useDailyReminder({ loading, expiringTodayRows }) {
  const [open, setOpen] = useState(false);
  const closeHandledRef = useRef(false);

  useEffect(() => {
    if (loading) return;
    if (expiringTodayRows.length === 0) {
      setOpen(false);
      return;
    }
    const todayStr = formatLocalYMD(new Date());
    if (localStorage.getItem(LS_DAILY_REMINDER_NOTIFIED) === todayStr) return;
    const snooze = localStorage.getItem(LS_DAILY_REMINDER_SNOOZE);
    if (snooze && todayStr < snooze) return;
    setOpen(true);
  }, [loading, expiringTodayRows]);

  const close = (kind) => {
    closeHandledRef.current = true;
    const todayStr = formatLocalYMD(new Date());
    if (kind === 'notified') {
      localStorage.setItem(LS_DAILY_REMINDER_NOTIFIED, todayStr);
    } else {
      localStorage.setItem(LS_DAILY_REMINDER_SNOOZE, tomorrowYMD());
    }
    setOpen(false);
  };

  /** Call from Radix's onOpenChange — preserves "snooze on dismiss" behaviour. */
  const onOpenChange = (nextOpen) => {
    if (nextOpen) {
      setOpen(true);
      return;
    }
    if (closeHandledRef.current) {
      closeHandledRef.current = false;
      return;
    }
    localStorage.setItem(LS_DAILY_REMINDER_SNOOZE, tomorrowYMD());
    setOpen(false);
  };

  return { open, onOpenChange, close };
}
