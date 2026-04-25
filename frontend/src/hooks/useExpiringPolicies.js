import { useMemo } from 'react';
import { CONTACT_STATUS, getEffectiveContactStatus } from '@/utils/contactStatus';
import { isRenewalOpen } from '@/utils/renewalResolution';
import { daysLeftUntil, parsePolicyEndDate } from '@/utils/policyDates';

/** Canonical insurance-type chips offered above the Expiry list. */
const CANONICAL_INSURANCE_TYPES = ['Motor', 'Health', 'Life', 'Travel', 'Property'];

/**
 * All Expiry-list derived data in one memoised hook.
 *
 * The dashboard previously declared ~6 ``useMemo`` blocks in-line; pulling
 * them here makes the component code declarative ("show me the rows")
 * and keeps the selector logic testable in isolation.
 *
 * @param {object[]} policies — full policy list from the API.
 * @param {object[]} customers — full customer list from the API.
 * @param {string} contactFilter — 'all' | 'not_contacted' | 'contacted_today' | 'follow_up'
 * @param {string} insuranceTypeFilter — 'all' | <lowercased insurance type name>
 */
export function useExpiringPolicies(policies, customers, contactFilter, insuranceTypeFilter) {
  const expiringSoonRows = useMemo(() => {
    const byId = Object.fromEntries(customers.map((c) => [String(c.id), c]));
    const rows = [];
    for (const p of policies) {
      if (p.status !== 'active') continue;
      const end = parsePolicyEndDate(p.end_date);
      if (!end) continue;
      const daysLeft = daysLeftUntil(end);
      if (daysLeft < 0 || daysLeft > 30) continue;
      const cust = byId[String(p.customer_id)];
      const insuranceTypeName =
        (p.insurance_type_name && String(p.insurance_type_name).trim()) || '';
      const policyTypeName =
        (p.policy_type_name && String(p.policy_type_name).trim()) ||
        (p.policy_type && String(p.policy_type).trim()) ||
        '';
      rows.push({
        policyId: p.id,
        customerName: cust?.name?.trim() || '—',
        phone: cust?.phone && String(cust.phone).trim() ? String(cust.phone).trim() : '',
        insuranceType: insuranceTypeName || '—',
        insuranceTypeKey: insuranceTypeName.toLowerCase(),
        policyType: policyTypeName || '—',
        policyNumber: (p.policy_number && String(p.policy_number).trim()) || '—',
        endDate: end,
        daysLeft,
        last_contacted_at: p.last_contacted_at ?? null,
        contact_status: p.contact_status ?? CONTACT_STATUS.NOT_CONTACTED,
        follow_up_date: p.follow_up_date ?? null,
      });
    }
    rows.sort((a, b) => a.daysLeft - b.daysLeft);
    return rows;
  }, [policies, customers]);

  const expiringCounts = useMemo(
    () => ({
      d7: expiringSoonRows.filter((r) => r.daysLeft <= 7).length,
      d15: expiringSoonRows.filter((r) => r.daysLeft <= 15).length,
      d30: expiringSoonRows.length,
    }),
    [expiringSoonRows]
  );

  const expiringTodayRows = useMemo(
    () => expiringSoonRows.filter((r) => r.daysLeft === 0),
    [expiringSoonRows]
  );

  /**
   * Always show the canonical Motor/Health/Life/Travel/Property chips,
   * plus any extra type that actually appears in the current expiring
   * rows so dynamic categories (e.g. an admin-added "Cyber") still get
   * a one-click filter.
   */
  const expiryInsuranceTypeOptions = useMemo(() => {
    const seen = new Map();
    for (const name of CANONICAL_INSURANCE_TYPES) seen.set(name.toLowerCase(), name);
    for (const row of expiringSoonRows) {
      const raw = row.insuranceType;
      if (!raw || raw === '—') continue;
      const key = raw.toLowerCase();
      if (!seen.has(key)) seen.set(key, raw);
    }
    return Array.from(seen, ([key, label]) => ({ key, label }));
  }, [expiringSoonRows]);

  const filteredExpiringSoonRows = useMemo(() => {
    return expiringSoonRows.filter((row) => {
      if (contactFilter !== 'all') {
        const eff = getEffectiveContactStatus(row);
        if (contactFilter === 'not_contacted' && eff !== CONTACT_STATUS.NOT_CONTACTED) {
          return false;
        }
        if (contactFilter === 'contacted_today' && eff !== CONTACT_STATUS.CONTACTED_TODAY) {
          return false;
        }
        if (contactFilter === 'follow_up' && eff !== CONTACT_STATUS.FOLLOW_UP) {
          return false;
        }
      }
      if (insuranceTypeFilter !== 'all') {
        if ((row.insuranceTypeKey || '') !== insuranceTypeFilter) return false;
      }
      return true;
    });
  }, [expiringSoonRows, contactFilter, insuranceTypeFilter]);

  /** Active policies past expiry whose renewal is still flagged Open. */
  const missedExpiredOpenCount = useMemo(() => {
    let n = 0;
    for (const p of policies) {
      if (p.status !== 'active') continue;
      const end = parsePolicyEndDate(p.end_date);
      if (!end) continue;
      if (daysLeftUntil(end) >= 0) continue;
      if (!isRenewalOpen(p)) continue;
      n += 1;
    }
    return n;
  }, [policies]);

  return {
    expiringSoonRows,
    expiringCounts,
    expiringTodayRows,
    expiryInsuranceTypeOptions,
    filteredExpiringSoonRows,
    missedExpiredOpenCount,
  };
}
