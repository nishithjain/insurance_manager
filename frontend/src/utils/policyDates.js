/** Shared policy date parsing for dashboard / missed opportunities. */

export function parsePolicyEndDate(s) {
  if (!s) return null;
  const t = String(s).trim();
  if (t.length >= 10 && t[4] === '-' && t[7] === '-') {
    const d = new Date(t.slice(0, 10));
    return Number.isNaN(d.getTime()) ? null : d;
  }
  const m = t.match(/^(\d{1,2})-(\d{1,2})-(\d{4})$/);
  if (m) {
    const d = new Date(Number(m[3]), Number(m[2]) - 1, Number(m[1]));
    return Number.isNaN(d.getTime()) ? null : d;
  }
  return null;
}

export function startOfDay(d) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

/** Whole days from today until end date (0 = expires today). */
export function daysLeftUntil(endDate) {
  const today = startOfDay(new Date());
  const end = startOfDay(endDate);
  return Math.round((end - today) / 86400000);
}
