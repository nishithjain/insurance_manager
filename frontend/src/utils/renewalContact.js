/**
 * Phone and WhatsApp helpers for renewal reminders (expiry dashboard).
 * wa.me expects digits only (no +). tel: uses E.164 with leading +.
 */

/**
 * Strip to digits; if local 10-digit (India mobile), prepend 91.
 * @param {string|null|undefined} phone
 * @returns {string} digits only, or "" if unusable
 */
export function sanitizePhoneNumber(phone) {
  if (phone == null || phone === '') return '';
  const s = String(phone).trim();
  if (!s) return '';
  let digits = s.replace(/\D/g, '');
  if (!digits) return '';
  if (digits.length === 11 && digits.startsWith('0')) {
    digits = digits.slice(1);
  }
  if (digits.length === 10) {
    digits = `91${digits}`;
  }
  return digits;
}

/** Digits-only number for https://wa.me/{digits} */
export function formatPhoneForWhatsApp(phone) {
  return sanitizePhoneNumber(phone);
}

/**
 * Pre-filled renewal text for WhatsApp / SMS (no policy number).
 * @param {{ customerName?: string, policyType?: string, endDate: Date }} row
 */
export function buildWhatsAppMessage(row) {
  const name = (row.customerName && String(row.customerName).trim()) || 'Customer';
  const policyTypeRaw = (row.policyType && String(row.policyType).trim()) || 'insurance';
  const policyTypeLower = policyTypeRaw.toLowerCase();
  const end = row.endDate instanceof Date ? row.endDate : new Date(row.endDate);
  const dateStr = Number.isNaN(end.getTime())
    ? '—'
    : end.toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      });
  return `Hi ${name}, your ${policyTypeLower} policy is expiring on ${dateStr}. Please renew it on time. Kindly contact Sandesh (9886065565) or Samraj (9886120280) for renewal assistance.`;
}

/**
 * @param {{ phone?: string, customerName?: string, policyType?: string, endDate: Date }} row
 * @returns {string|null}
 */
export function getWhatsAppUrl(row) {
  const digits = formatPhoneForWhatsApp(row.phone);
  if (!digits) return null;
  const message = buildWhatsAppMessage(row);
  return `https://wa.me/${digits}?text=${encodeURIComponent(message)}`;
}

/**
 * @param {string|null|undefined} phone
 * @returns {string|null}
 */
export function getCallUrl(phone) {
  const digits = sanitizePhoneNumber(phone);
  if (!digits) return null;
  return `tel:+${digits}`;
}

/** E.164-style string for clipboard (+country digits), same as tel: without the scheme. */
export function getPhoneNumberForClipboard(phone) {
  const digits = sanitizePhoneNumber(phone);
  if (!digits) return null;
  return `+${digits}`;
}

/**
 * Copy customer phone to clipboard (for use with Call alongside tel:).
 * @returns {Promise<boolean>}
 */
export async function copyCustomerPhoneToClipboard(phone) {
  const text = getPhoneNumberForClipboard(phone);
  if (!text) return false;
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.left = '-9999px';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }
}

/**
 * @param {{ phone?: string, customerName?: string, policyType?: string, endDate: Date }} row
 * @returns {string|null}
 */
export function getSmsUrl(row) {
  const digits = sanitizePhoneNumber(row.phone);
  if (!digits) return null;
  const message = buildWhatsAppMessage(row);
  return `sms:${digits}?body=${encodeURIComponent(message)}`;
}

/**
 * Dev/debug: log sample rows (original phone, sanitized, message, WhatsApp URL).
 * @param {Array<object>} rows
 * @param {number} limit
 */
export function logRenewalContactDebug(rows, limit = 3) {
  const slice = rows.slice(0, limit);
  slice.forEach((row, i) => {
    const originalPhone = row.phone;
    const sanitizedPhone = sanitizePhoneNumber(row.phone);
    const message = buildWhatsAppMessage(row);
    const whatsappUrl = getWhatsAppUrl(row);
    console.info('[renewal-contact]', {
      index: i,
      policyId: row.policyId,
      originalPhone,
      sanitizedPhone,
      message,
      whatsappUrl,
    });
  });
}
