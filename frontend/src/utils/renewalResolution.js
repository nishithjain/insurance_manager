/** Expired-policy renewal resolution (backend enum strings). */

export const RENEWAL_STATUS = {
  OPEN: 'Open',
  RENEWED_WITH_US: 'RenewedWithUs',
  RENEWED_ELSEWHERE: 'RenewedElsewhere',
  NOT_INTERESTED: 'NotInterested',
  POLICY_CLOSED: 'PolicyClosed',
  DUPLICATE: 'Duplicate',
};

/** Resolvable statuses (exclude Open — use reopen flow). */
export const RESOLVED_RENEWAL_OPTIONS = [
  { value: RENEWAL_STATUS.RENEWED_WITH_US, label: 'Renewed With Us' },
  { value: RENEWAL_STATUS.RENEWED_ELSEWHERE, label: 'Renewed Elsewhere' },
  { value: RENEWAL_STATUS.NOT_INTERESTED, label: 'Not Interested' },
  { value: RENEWAL_STATUS.POLICY_CLOSED, label: 'Policy Closed / No Longer Needed' },
  { value: RENEWAL_STATUS.DUPLICATE, label: 'Duplicate / Invalid' },
];

export const RENEWAL_STATUS_LABELS = {
  [RENEWAL_STATUS.OPEN]: 'Open',
  [RENEWAL_STATUS.RENEWED_WITH_US]: 'Renewed With Us',
  [RENEWAL_STATUS.RENEWED_ELSEWHERE]: 'Renewed Elsewhere',
  [RENEWAL_STATUS.NOT_INTERESTED]: 'Not Interested',
  [RENEWAL_STATUS.POLICY_CLOSED]: 'Policy Closed',
  [RENEWAL_STATUS.DUPLICATE]: 'Duplicate',
};

export function getRenewalStatusLabel(status) {
  if (!status) return RENEWAL_STATUS_LABELS[RENEWAL_STATUS.OPEN];
  return RENEWAL_STATUS_LABELS[status] || status;
}

export function isRenewalOpen(policy) {
  const s = policy?.renewal_status || RENEWAL_STATUS.OPEN;
  return s === RENEWAL_STATUS.OPEN;
}
