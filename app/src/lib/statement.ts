// Statement date ranges. Days are Turkish days (UTC+3 all year), as in backend/app/statement.py.

const TR_OFFSET_MS = 3 * 60 * 60 * 1000;

/** Mirrors the API (MAX_STATEMENT_DAYS). */
export const MAX_STATEMENT_DAYS = 366;

export type DateRange = { from: string; to: string }; // ISO YYYY-MM-DD, inclusive

export type RangePreset = 'thisMonth' | 'last30' | 'last90';

function isoDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** Today's date in Turkey, whatever the device's time zone. */
export function turkishToday(now: Date = new Date()): string {
  return isoDay(new Date(now.getTime() + TR_OFFSET_MS));
}

function addDays(iso: string, days: number): string {
  const date = new Date(`${iso}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return isoDay(date);
}

export function presetRange(preset: RangePreset, now: Date = new Date()): DateRange {
  const to = turkishToday(now);
  if (preset === 'thisMonth') return { from: `${to.slice(0, 8)}01`, to };
  return { from: addDays(to, preset === 'last30' ? -29 : -89), to };
}

/** Days in an inclusive range; negative when `from` is after `to`. */
export function rangeDays({ from, to }: DateRange): number {
  const ms = new Date(`${to}T00:00:00Z`).getTime() - new Date(`${from}T00:00:00Z`).getTime();
  return Math.round(ms / 86_400_000) + 1;
}

/** Turkish message for an unusable range, or null when it can be requested. */
export function rangeError(range: DateRange): string | null {
  const days = rangeDays(range);
  if (days < 1) return 'Başlangıç tarihi bitiş tarihinden sonra olamaz.';
  if (days > MAX_STATEMENT_DAYS) return `Ekstre en fazla ${MAX_STATEMENT_DAYS} günü kapsayabilir.`;
  return null;
}

/** Same name as the API's Content-Disposition: ABBank-ekstre-1234-20261101-20261130.csv. */
export function statementFilename(iban: string, { from, to }: DateRange): string {
  return `ABBank-ekstre-${iban.slice(-4)}-${from.replaceAll('-', '')}-${to.replaceAll('-', '')}.csv`;
}

/** "2026-11-01" → "01.11.2026" */
export function formatIsoDate(iso: string): string {
  const [y, m, d] = iso.split('-');
  return `${d}.${m}.${y}`;
}

/**
 * The API's CSV starts with a byte-order mark so Excel reads it as UTF-8, but
 * `Response.text()` strips it; put it back before the text becomes a file.
 */
export function withBom(csv: string): string {
  return csv.startsWith('\uFEFF') ? csv : `\uFEFF${csv}`;
}

/**
 * A tr-TR date formatter in Turkish time, the same days the range filter uses. Falls back to the
 * device's zone if the JS engine rejects the zone, so a screen never fails to load over it.
 */
export function turkishDateFormatter(options: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  try {
    return new Intl.DateTimeFormat('tr-TR', { ...options, timeZone: 'Europe/Istanbul' });
  } catch {
    return new Intl.DateTimeFormat('tr-TR', options);
  }
}
