// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

// @ts-ignore -- Node's native TypeScript runner requires the .ts extension.
import { toCustomer, toMovement, toTransferResult, totalBalance } from './models.ts';

const me = { customer_no: '123456789', full_name: 'Deniz Yılmaz' };
const accounts = [
  { id: 1, kind: 'checking' as const, name: 'Vadesiz', iban: 'TR01', balance_kurus: 1_245_075, goal_kurus: null },
  { id: 2, kind: 'savings' as const, name: 'Birikim', iban: 'TR02', balance_kurus: 3_820_000, goal_kurus: 5_000_000 },
];

test('toCustomer API alanlarını uygulama alanlarına eşler', () => {
  assert.deepEqual(toCustomer(me, accounts), {
    customerNo: '123456789',
    fullName: 'Deniz Yılmaz',
    accounts: [
      { id: 1, kind: 'checking', name: 'Vadesiz', iban: 'TR01', balanceKurus: 1_245_075, goalKurus: null },
      { id: 2, kind: 'savings', name: 'Birikim', iban: 'TR02', balanceKurus: 3_820_000, goalKurus: 5_000_000 },
    ],
  });
});

test('toCustomer hesabı olmayan müşteride boş liste verir', () => {
  assert.deepEqual(toCustomer(me, []).accounts, []);
});

test('totalBalance tüm hesapları kuruş olarak toplar', () => {
  assert.equal(totalBalance(toCustomer(me, accounts)), 5_065_075);
  assert.equal(totalBalance(toCustomer(me, [])), 0);
});

test('toMovement ve toTransferResult alanları eşler', () => {
  assert.deepEqual(
    toMovement({ id: 5, amount_kurus: -50_000, balance_after_kurus: 1_195_075, description: 'Kira', counterparty: 'Al*** Ka***', created_at: '2026-10-28T13:37:26Z' }),
    { id: 5, amountKurus: -50_000, balanceAfterKurus: 1_195_075, description: 'Kira', counterparty: 'Al*** Ka***', createdAt: '2026-10-28T13:37:26Z' },
  );
  assert.deepEqual(
    toTransferResult({ id: 2, from_account_id: 1, to_iban: 'TR26', recipient: 'Al*** Ka***', amount_kurus: 150_000, description: 'Kira payı', from_balance_after_kurus: 1_045_075, created_at: 'x' }),
    { id: 2, fromAccountId: 1, toIban: 'TR26', recipient: 'Al*** Ka***', amountKurus: 150_000, description: 'Kira payı', fromBalanceAfterKurus: 1_045_075, createdAt: 'x' },
  );
});
