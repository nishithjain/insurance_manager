package com.insurance.mobile.core.util

import java.time.LocalDate
import java.time.ZoneId
import java.time.format.DateTimeParseException
import java.time.temporal.ChronoUnit

/**
 * Parses policy end dates from API strings (ISO date or date-time). Uses the first 10 chars when
 * they look like `yyyy-MM-dd`.
 *
 * **API ADJUSTMENT:** If the backend changes date format, update this parser.
 */
fun parsePolicyEndDate(raw: String?): LocalDate? {
    if (raw.isNullOrBlank()) return null
    val s = raw.trim()
    return try {
        if (s.length >= 10 && s[4] == '-' && s[7] == '-') {
            LocalDate.parse(s.substring(0, 10))
        } else {
            LocalDate.parse(s)
        }
    } catch (_: DateTimeParseException) {
        null
    }
}

fun todayLocal(zoneId: ZoneId = ZoneId.systemDefault()): LocalDate =
    LocalDate.now(zoneId)

/** Whole days from today until [end] (0 = expires today, negative = already expired). */
fun daysUntilExpiry(end: LocalDate, zoneId: ZoneId = ZoneId.systemDefault()): Long {
    val today = todayLocal(zoneId)
    return ChronoUnit.DAYS.between(today, end)
}
