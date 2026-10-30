// Amounts are integer kuruş everywhere (API and app) to avoid floating-point rounding.

const tryFormatter = new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' });

export function formatKurus(kurus: number): string {
  return tryFormatter.format(kurus / 100);
}

/** Share of the goal reached, clamped to 0–1. */
export function goalProgress(balanceKurus: number, goalKurus: number): number {
  if (goalKurus <= 0) return 1;
  return Math.min(1, Math.max(0, balanceKurus / goalKurus));
}

/**
 * Parses a lira amount as Turkish users type it into kuruş, or null if it isn't a valid amount.
 * "1.234,56" → 123456 · "250" → 25000 · "12,5" → 1250 · "1.500" → 150000 (dot = thousands).
 * Works on the string digits, never on floats, so no rounding errors.
 */
export function parseTryAmount(input: string): number | null {
  let text = input.replace(/[\s₺]/g, '').replace(/TL$/i, '');
  if (text.includes(',')) {
    // Comma is the decimal separator; dots before it must be proper thousands groups.
    if (!/^(\d{1,3}(\.\d{3})+|\d+),\d{1,2}$/.test(text)) return null;
    text = text.replace(/\./g, '').replace(',', '.');
  } else if (/^\d{1,3}(\.\d{3})+$/.test(text)) {
    text = text.replace(/\./g, '');
  }
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(text);
  if (!match) return null;
  const lira = match[1].replace(/^0+(?=\d)/, '');
  if (lira.length > 12) return null;
  const kurus = Number(lira) * 100 + Number((match[2] ?? '').padEnd(2, '0'));
  return kurus > 0 ? kurus : null;
}
