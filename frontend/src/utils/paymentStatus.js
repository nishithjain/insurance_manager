/**
 * Payment status labels (aligned with backend payment_statuses + PATCH allow-list).
 * Add new values here and in backend ALLOWED_PAYMENT_UPDATE_FROM_PENDING / DB seed as needed.
 */

/** @readonly */
export const PAYMENT_STATUS = Object.freeze({
  PENDING: 'PENDING',
  CUSTOMER_ONLINE: 'CUSTOMER ONLINE',
  CUSTOMER_CHEQUE: 'CUSTOMER CHEQUE',
  TRANSFER_TO_SAMRAJ: 'TRANSFER TO SAMRAJ',
  CASH_TO_SAMRAJ: 'CASH TO SAMRAJ',
  CASH_TO_SANDESH: 'CASH TO SANDESH',
});

/** All known labels for display / badges (extend when adding statuses). */
export const ALL_PAYMENT_STATUS_LABELS = Object.freeze([
  PAYMENT_STATUS.PENDING,
  PAYMENT_STATUS.CUSTOMER_ONLINE,
  PAYMENT_STATUS.CUSTOMER_CHEQUE,
  PAYMENT_STATUS.TRANSFER_TO_SAMRAJ,
  PAYMENT_STATUS.CASH_TO_SAMRAJ,
  PAYMENT_STATUS.CASH_TO_SANDESH,
  'Paid',
  'Partial',
  'Unknown',
]);

/** Statuses allowed when updating from the Pending Payments workflow (not PENDING). */
export const PAYMENT_UPDATE_OPTIONS_FROM_PENDING = Object.freeze([
  PAYMENT_STATUS.CUSTOMER_ONLINE,
  PAYMENT_STATUS.CUSTOMER_CHEQUE,
  PAYMENT_STATUS.TRANSFER_TO_SAMRAJ,
  PAYMENT_STATUS.CASH_TO_SAMRAJ,
  PAYMENT_STATUS.CASH_TO_SANDESH,
]);

/**
 * Normalize for comparison (DB may have mixed case from imports).
 * @param {string|null|undefined} s
 */
export function normalizePaymentStatus(s) {
  return (s == null ? '' : String(s)).trim().toUpperCase();
}

/**
 * @param {string|null|undefined} s
 */
export function isPendingPaymentStatus(s) {
  return normalizePaymentStatus(s) === 'PENDING';
}

/**
 * Tailwind-oriented classes for status pills (pending = warm alert; settled = cool/green).
 * @param {string|null|undefined} status
 */
export function getPaymentStatusBadgeClass(status) {
  const n = normalizePaymentStatus(status);
  if (n === 'PENDING') {
    return 'bg-amber-100 text-amber-950 border-amber-300';
  }
  if (
    n === 'CUSTOMER ONLINE' ||
    n === 'CUSTOMER CHEQUE' ||
    n === 'TRANSFER TO SAMRAJ' ||
    n === 'CASH TO SAMRAJ' ||
    n === 'CASH TO SANDESH'
  ) {
    return 'bg-emerald-50 text-emerald-900 border-emerald-200';
  }
  if (n === 'PAID' || n === 'PARTIAL') {
    return 'bg-sky-50 text-sky-900 border-sky-200';
  }
  return 'bg-slate-100 text-slate-800 border-slate-200';
}
