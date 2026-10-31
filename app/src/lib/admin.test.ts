// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

// @ts-ignore -- Node's native TypeScript runner requires the .ts extension.
import {
  actionAuthor,
  describeAction,
  isValidReason,
  toAdminAction,
  toAdminCustomer,
} from './admin.ts';

test('toAdminCustomer API alanlarını eşler', () => {
  assert.deepEqual(
    toAdminCustomer({
      id: 2, customer_no: '123456789', full_name: 'Deniz Yılmaz', is_admin: false,
      locked: true, account_count: 2, created_at: 'x',
    }),
    {
      id: 2, customerNo: '123456789', fullName: 'Deniz Yılmaz', isAdmin: false,
      locked: true, accountCount: 2, createdAt: 'x',
    },
  );
});

test('describeAction işlemi, müşteriyi ve varsa hesabı yazar', () => {
  const freeze = toAdminAction({
    id: 1, action: 'freeze_account', admin_customer_no: '555555555', customer_no: '123456789',
    account_id: 4, reason: 'Şüpheli işlem', created_at: 'x',
  });
  assert.equal(describeAction(freeze), 'Hesap donduruldu · 123456789 · hesap #4');
  assert.equal(
    describeAction({ ...freeze, action: 'unlock_customer', accountId: null }),
    'Giriş kilidi açıldı · 123456789',
  );
});

test('actionAuthor sunucuda yapılan değişikliği belirtir', () => {
  const grant = toAdminAction({
    id: 2, action: 'grant_admin', admin_customer_no: null, customer_no: '987654321',
    account_id: null, reason: 'Operasyon ekibi', created_at: 'x',
  });
  assert.equal(actionAuthor(grant), 'sunucu (komut satırı)');
  assert.equal(describeAction(grant), 'Yönetici yetkisi verildi · 987654321');
  assert.equal(actionAuthor({ ...grant, adminCustomerNo: '555555555' }), '555555555');
});

test('isValidReason API ile aynı sınırları uygular', () => {
  assert.equal(isValidReason(''), false);
  assert.equal(isValidReason('  ab  '), false);
  assert.equal(isValidReason('abc'), true);
  assert.equal(isValidReason('x'.repeat(200)), true);
  assert.equal(isValidReason('x'.repeat(201)), false);
});
