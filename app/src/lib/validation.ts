// Form rules, matching the API's (backend/app/schemas.py) so users see errors before a request.
// Login: customer numbers are 9 digits, passwords are 6 digits (from the legacy app).

import { isValidNationalId } from './banking.ts';

export type LoginErrors = {
  customerNo?: string;
  password?: string;
};

export function validateLogin(customerNo: string, password: string): LoginErrors {
  const errors: LoginErrors = {};
  const no = customerNo.trim();

  if (!no) errors.customerNo = 'Müşteri numaranızı girin.';
  else if (!/^\d{9}$/.test(no)) errors.customerNo = 'Müşteri numarası 9 haneli olmalı.';

  if (!password) errors.password = 'Şifrenizi girin.';
  else if (!/^\d{6}$/.test(password)) errors.password = 'Şifre 6 haneli olmalı.';

  return errors;
}

/** Keeps only digits and caps the length, for numeric-only inputs. */
export function digitsOnly(value: string, maxLength: number): string {
  return value.replace(/\D/g, '').slice(0, maxLength);
}

/** Inserts dots while typing a date: "20051995" → "20.05.1995". */
export function formatDateInput(value: string): string {
  const d = digitsOnly(value, 8);
  return [d.slice(0, 2), d.slice(2, 4), d.slice(4)].filter(Boolean).join('.');
}

/** "GG.AA.YYYY" → "YYYY-MM-DD", or null if it isn't a real calendar date. */
export function parseTrDate(value: string): string | null {
  const match = /^(\d{2})\.(\d{2})\.(\d{4})$/.exec(value.trim());
  if (!match) return null;
  const [, dd, mm, yyyy] = match;
  const date = new Date(Date.UTC(Number(yyyy), Number(mm) - 1, Number(dd)));
  const real =
    date.getUTCFullYear() === Number(yyyy) &&
    date.getUTCMonth() === Number(mm) - 1 &&
    date.getUTCDate() === Number(dd);
  return real ? `${yyyy}-${mm}-${dd}` : null;
}

/** Full years between an ISO birth date and `today` (defaults to now). */
export function ageOn(isoBirthDate: string, today: Date = new Date()): number {
  const [y, m, d] = isoBirthDate.split('-').map(Number);
  const before = today.getMonth() + 1 < m || (today.getMonth() + 1 === m && today.getDate() < d);
  return today.getFullYear() - y - (before ? 1 : 0);
}

export type RegisterFields = {
  nationalId: string;
  fullName: string;
  birthDate: string; // as typed: GG.AA.YYYY
  password: string;
  passwordRepeat: string;
};

export type RegisterErrors = Partial<Record<keyof RegisterFields, string>>;

export function validateRegister(f: RegisterFields, today: Date = new Date()): RegisterErrors {
  const errors: RegisterErrors = {};

  if (!f.nationalId) errors.nationalId = 'T.C. kimlik numaranızı girin.';
  else if (!isValidNationalId(f.nationalId)) errors.nationalId = 'T.C. kimlik numarası geçersiz.';

  const name = f.fullName.trim().replace(/\s+/g, ' ');
  if (!name) errors.fullName = 'Adınızı ve soyadınızı girin.';
  else if (name.length < 3 || !/^[\p{L} ]+$/u.test(name))
    errors.fullName = 'Ad soyad yalnızca harflerden oluşmalı.';

  const iso = parseTrDate(f.birthDate);
  if (!f.birthDate) errors.birthDate = 'Doğum tarihinizi girin.';
  else if (!iso) errors.birthDate = 'Tarihi GG.AA.YYYY biçiminde girin.';
  else {
    const age = ageOn(iso, today);
    if (age < 0 || age > 120) errors.birthDate = 'Doğum tarihi geçersiz.';
    else if (age < 18) errors.birthDate = 'Hesap açmak için 18 yaşından büyük olmalısınız.';
  }

  if (!f.password) errors.password = 'Bir şifre belirleyin.';
  else if (!/^\d{6}$/.test(f.password)) errors.password = 'Şifre 6 haneli olmalı.';
  else if (
    /^(\d)\1{5}$/.test(f.password) ||
    '0123456789'.includes(f.password) ||
    '9876543210'.includes(f.password)
  )
    errors.password = 'Tahmin edilmesi kolay bir şifre seçmeyin (111111, 123456 gibi).';

  if (!f.passwordRepeat) errors.passwordRepeat = 'Şifrenizi tekrar girin.';
  else if (f.passwordRepeat !== f.password) errors.passwordRepeat = 'Şifreler eşleşmiyor.';

  return errors;
}
