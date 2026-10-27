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
