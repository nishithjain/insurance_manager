/** Renewal contact tracking — aligns with backend policy contact fields. */

export const CONTACT_STATUS = {
  NOT_CONTACTED: 'Not Contacted',
  CONTACTED_TODAY: 'Contacted Today',
  FOLLOW_UP: 'Follow-up Needed',
};

export const CONTACT_STATUS_OPTIONS = [
  CONTACT_STATUS.NOT_CONTACTED,
  CONTACT_STATUS.CONTACTED_TODAY,
  CONTACT_STATUS.FOLLOW_UP,
];

/** Local calendar: is ISO datetime's date the same as today? */
export function isContactedToday(isoString) {
  if (!isoString || typeof isoString !== 'string') return false;
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return false;
  const t0 = new Date();
  return (
    d.getFullYear() === t0.getFullYear() &&
    d.getMonth() === t0.getMonth() &&
    d.getDate() === t0.getDate()
  );
}

/**
 * Effective status for UI (see product rules):
 * - Follow-up Needed always wins when stored as such.
 * - Else if last_contacted_at is today → Contacted Today.
 * - Else Not Contacted (even if DB still says "Contacted Today" from a prior day).
 */
export function getEffectiveContactStatus(policy) {
  const stored = policy?.contact_status || CONTACT_STATUS.NOT_CONTACTED;
  if (stored === CONTACT_STATUS.FOLLOW_UP) return CONTACT_STATUS.FOLLOW_UP;
  if (policy?.last_contacted_at && isContactedToday(policy.last_contacted_at)) {
    return CONTACT_STATUS.CONTACTED_TODAY;
  }
  return CONTACT_STATUS.NOT_CONTACTED;
}

export function nowIso() {
  return new Date().toISOString();
}

/** Payload for Call / WhatsApp — marks contacted now. */
export function buildPatchMarkContacted() {
  return {
    last_contacted_at: nowIso(),
    contact_status: CONTACT_STATUS.CONTACTED_TODAY,
    follow_up_date: null,
  };
}

export function buildPatchFollowUp(followUpDateYmd) {
  return {
    contact_status: CONTACT_STATUS.FOLLOW_UP,
    follow_up_date: followUpDateYmd || null,
    last_contacted_at: null,
  };
}

export function buildPatchContactStatus(status, followUpDateYmd) {
  if (status === CONTACT_STATUS.FOLLOW_UP) {
    return buildPatchFollowUp(followUpDateYmd);
  }
  if (status === CONTACT_STATUS.CONTACTED_TODAY) {
    return {
      contact_status: CONTACT_STATUS.CONTACTED_TODAY,
      last_contacted_at: nowIso(),
      follow_up_date: null,
    };
  }
  return {
    contact_status: CONTACT_STATUS.NOT_CONTACTED,
    last_contacted_at: null,
    follow_up_date: null,
  };
}

/** API payload: mark as just contacted (shared by Call / WhatsApp). */
export function markAsContacted() {
  return buildPatchMarkContacted();
}

/** API payload: schedule follow-up */
export function markAsFollowUp(followUpDateYmd) {
  return buildPatchFollowUp(followUpDateYmd);
}

/** API payload: set status from dropdown */
export function updateContactStatus(status, followUpDateYmd) {
  return buildPatchContactStatus(status, followUpDateYmd);
}

/** Default follow-up date: 7 days from today (YYYY-MM-DD). */
export function defaultFollowUpDateYmd() {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().slice(0, 10);
}

export function statusDisplayMeta(effectiveStatus) {
  switch (effectiveStatus) {
    case CONTACT_STATUS.CONTACTED_TODAY:
      return { emoji: '🟢', label: 'Contacted Today', tone: 'contacted' };
    case CONTACT_STATUS.FOLLOW_UP:
      return { emoji: '🟡', label: 'Follow-up Needed', tone: 'followup' };
    default:
      return { emoji: '🔴', label: 'Not Contacted', tone: 'none' };
  }
}
