import { isPendingPaymentStatus, normalizePaymentStatus } from '@/utils/paymentStatus';
import { parsePolicyEndDate, daysLeftUntil } from '@/utils/policyDates';

/**
 * @param {object[]} policies
 * @param {Record<string, object>} customersById keyed by customer id string
 * @returns {Array<{
 *   policy: object,
 *   customerName: string,
 *   phone: string,
 *   endDate: Date|null,
 *   daysLeft: number|null,
 * }>}
 */
export function getPendingPaymentRows(policies, customersById) {
  const rows = [];
  for (const p of policies || []) {
    if (!isPendingPaymentStatus(p.payment_status)) continue;
    const cid = String(p.customer_id);
    const cust = customersById[cid];
    const customerName = (cust?.name && String(cust.name).trim()) || '—';
    const phone = (cust?.phone && String(cust.phone).trim()) || '';
    const endDate = parsePolicyEndDate(p.end_date);
    const daysLeft = endDate ? daysLeftUntil(endDate) : null;
    rows.push({
      policy: p,
      customerName,
      phone,
      endDate,
      daysLeft,
    });
  }
  return rows;
}

/**
 * @param {ReturnType<typeof getPendingPaymentRows>} rows
 * @param {string} q
 */
export function filterPendingRowsBySearch(rows, q) {
  const s = (q || '').trim().toLowerCase();
  if (!s) return rows;
  return rows.filter((r) => {
    const insuranceType =
      (r.policy.insurance_type_name && String(r.policy.insurance_type_name).toLowerCase()) || '';
    const policyType =
      (r.policy.policy_type_name && String(r.policy.policy_type_name).toLowerCase()) ||
      (r.policy.policy_type && String(r.policy.policy_type).toLowerCase()) ||
      '';
    const ph = (r.phone || '').toLowerCase();
    const cn = (r.customerName || '').toLowerCase();
    return cn.includes(s) || insuranceType.includes(s) || policyType.includes(s) || ph.includes(s);
  });
}

/**
 * @param {ReturnType<typeof getPendingPaymentRows>} rows
 * @param {'expiry_asc'|'name_asc'} sortBy
 */
export function sortPendingRows(rows, sortBy) {
  const copy = [...rows];
  if (sortBy === 'name_asc') {
    copy.sort((a, b) =>
      (a.customerName || '').localeCompare(b.customerName || '', undefined, { sensitivity: 'base' })
    );
    return copy;
  }
  // expiry_asc: sooner expiry first; missing dates last
  copy.sort((a, b) => {
    if (!a.endDate && !b.endDate) return 0;
    if (!a.endDate) return 1;
    if (!b.endDate) return -1;
    return a.endDate.getTime() - b.endDate.getTime();
  });
  return copy;
}

/**
 * @param {ReturnType<typeof getPendingPaymentRows>} rows
 */
export function summarizePendingPayments(rows) {
  let totalPremium = 0;
  for (const r of rows) {
    const v = r.policy?.premium;
    const n = v == null ? NaN : Number(v);
    if (!Number.isNaN(n)) totalPremium += n;
  }
  return {
    count: rows.length,
    totalPremium,
  };
}

/**
 * Highlight when expiry is within `withinDays` (inclusive).
 * @param {number|null} daysLeft
 * @param {number} withinDays
 */
export function isUrgentExpiry(daysLeft, withinDays = 7) {
  if (daysLeft == null) return false;
  return daysLeft >= 0 && daysLeft <= withinDays;
}
