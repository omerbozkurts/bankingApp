// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

// @ts-ignore -- Node's native TypeScript runner requires the .ts extension.
import { toCustomer, totalBalance } from './models.ts';

const me = { customer_no: '123456789', full_name: 'Deniz Yılmaz' };
const accounts = [
  { id: 1, name: 'Vadesiz', iban: 'TR01', balance_kurus: 1_245_075, goal_kurus: null },
  { id: 2, name: 'Birikim', iban: 'TR02', balance_kurus: 3_820_000, goal_kurus: 5_000_000 },
];

test('toCustomer API alanlarını uygulama alanlarına eşler', () => {
  assert.deepEqual(toCustomer(me, accounts), {
    customerNo: '123456789',
    fullName: 'Deniz Yılmaz',
    accounts: [
      { id: 1, name: 'Vadesiz', iban: 'TR01', balanceKurus: 1_245_075, goalKurus: null },
      { id: 2, name: 'Birikim', iban: 'TR02', balanceKurus: 3_820_000, goalKurus: 5_000_000 },
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
