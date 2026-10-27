// Demo account for trying the app before the FastAPI backend exists.
// Replace checkDemoCredentials with the real login API call once the backend lands.

export type Account = {
  id: string;
  name: string;
  iban: string;
  /** Amounts are integer kuruş to avoid floating-point rounding. */
  balanceKurus: number;
  goalKurus?: number;
};

export type Customer = {
  customerNo: string;
  fullName: string;
  accounts: Account[];
};

export const DEMO_CREDENTIALS = {
  customerNo: '123456789',
  password: '123456',
} as const;

export const DEMO_CUSTOMER: Customer = {
  customerNo: DEMO_CREDENTIALS.customerNo,
  fullName: 'Deniz Yılmaz',
  accounts: [
    {
      id: 'vadesiz',
      name: 'Vadesiz TL Hesabı',
      iban: 'TR00 0000 0000 0000 0000 0000 01',
      balanceKurus: 1_245_075,
    },
    {
      id: 'birikim',
      name: 'Birikim Hesabı',
      iban: 'TR00 0000 0000 0000 0000 0000 02',
      balanceKurus: 3_820_000,
      goalKurus: 5_000_000,
    },
  ],
};

export function checkDemoCredentials(customerNo: string, password: string): Customer | null {
  return customerNo.trim() === DEMO_CREDENTIALS.customerNo && password === DEMO_CREDENTIALS.password
    ? DEMO_CUSTOMER
    : null;
}

const tryFormatter = new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' });

export function formatKurus(kurus: number): string {
  return tryFormatter.format(kurus / 100);
}

/** Share of the goal reached, clamped to 0–1. */
export function goalProgress(balanceKurus: number, goalKurus: number): number {
  if (goalKurus <= 0) return 1;
  return Math.min(1, Math.max(0, balanceKurus / goalKurus));
}
