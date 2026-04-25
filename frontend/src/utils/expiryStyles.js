/**
 * Tailwind class helpers for the dashboard "Expiry list" rows.
 *
 * Kept as pure functions so the table component stays presentational.
 */

import { CONTACT_STATUS } from './contactStatus';

/** 🔴 < 7 days, 🟠 < 15 days, 🟡 within 30 days. */
export function expiryRowUrgencyClass(daysLeft) {
  if (daysLeft < 7) return 'border-l-2 border-[#DC2626] bg-red-50/60';
  if (daysLeft < 15) return 'border-l-2 border-[#F59E0B] bg-orange-50/60';
  return 'border-l-2 border-yellow-400 bg-yellow-50/50';
}

/** Visual emphasis driven by the row's effective contact status. */
export function expiryRowContactClass(effectiveStatus) {
  if (effectiveStatus === CONTACT_STATUS.FOLLOW_UP) {
    return 'ring-1 ring-inset ring-amber-300/90 bg-amber-50/50';
  }
  if (effectiveStatus === CONTACT_STATUS.CONTACTED_TODAY) {
    return 'opacity-[0.88]';
  }
  return 'font-semibold';
}
