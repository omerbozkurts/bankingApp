// Login rules carried over from the legacy app (legacy/kullanici.py):
// customer numbers are 9 digits, passwords are 6 digits.

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
