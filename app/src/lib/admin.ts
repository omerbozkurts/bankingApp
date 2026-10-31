// Admin panel shapes, and their mapping from the API (backend/app/routers/admin.py).

import type { Account } from './models';

export type AdminCustomer = {
  id: number;
  customerNo: string;
  fullName: string;
  isAdmin: boolean;
  /** Temporarily locked after repeated wrong passwords. */
  locked: boolean;
  accountCount: number;
  createdAt: string;
};

export type AdminCustomerDetail = AdminCustomer & { accounts: Account[] };

export type AdminCustomerPage = { items: AdminCustomer[]; nextBeforeId: number | null };

export type AdminActionKind =
  | 'freeze_account'
  | 'unfreeze_account'
  | 'unlock_customer'
  | 'grant_admin'
  | 'revoke_admin';

export type AdminAction = {
  id: number;
  action: AdminActionKind;
  /** Null for changes made on the server (granting or revoking admin rights). */
  adminCustomerNo: string | null;
  customerNo: string;
  accountId: number | null;
  reason: string;
  createdAt: string;
};

export type AdminActionPage = { items: AdminAction[]; nextBeforeId: number | null };

export type ApiAdminCustomer = {
  id: number;
  customer_no: string;
  full_name: string;
  is_admin: boolean;
  locked: boolean;
  account_count: number;
  created_at: string;
};

export type ApiAdminAction = {
  id: number;
  action: AdminActionKind;
  admin_customer_no: string | null;
  customer_no: string;
  account_id: number | null;
  reason: string;
  created_at: string;
};

/** Same rule as the API: every change needs a reason someone can read later. */
export const MIN_REASON_LENGTH = 3;
export const MAX_REASON_LENGTH = 200;

export function isValidReason(reason: string): boolean {
  const length = reason.trim().length;
  return length >= MIN_REASON_LENGTH && length <= MAX_REASON_LENGTH;
}

export function toAdminCustomer(c: ApiAdminCustomer): AdminCustomer {
  return {
    id: c.id,
    customerNo: c.customer_no,
    fullName: c.full_name,
    isAdmin: c.is_admin,
    locked: c.locked,
    accountCount: c.account_count,
    createdAt: c.created_at,
  };
}

export function toAdminAction(a: ApiAdminAction): AdminAction {
  return {
    id: a.id,
    action: a.action,
    adminCustomerNo: a.admin_customer_no,
    customerNo: a.customer_no,
    accountId: a.account_id,
    reason: a.reason,
    createdAt: a.created_at,
  };
}

const ACTION_LABELS: Record<AdminActionKind, string> = {
  freeze_account: 'Hesap donduruldu',
  unfreeze_account: 'Hesap dondurması kaldırıldı',
  unlock_customer: 'Giriş kilidi açıldı',
  grant_admin: 'Yönetici yetkisi verildi',
  revoke_admin: 'Yönetici yetkisi kaldırıldı',
};

/** Who made the change: an admin's customer number, or the server's command line. */
export function actionAuthor(a: AdminAction): string {
  return a.adminCustomerNo === null ? 'sunucu (komut satırı)' : a.adminCustomerNo;
}

/** One line for the audit log: "Hesap donduruldu · 123456789 · hesap #4". */
export function describeAction(a: AdminAction): string {
  const parts = [ACTION_LABELS[a.action] ?? a.action, a.customerNo];
  if (a.accountId !== null) parts.push(`hesap #${a.accountId}`);
  return parts.join(' · ');
}
