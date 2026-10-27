// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

// @ts-ignore -- Node's native TypeScript runner requires the .ts extension.
import { checkDemoCredentials, DEMO_CREDENTIALS, DEMO_CUSTOMER, formatKurus, goalProgress } from './demo-account.ts';

test('doğru bilgiler aynı demo müşterisini döndürür', () => {
  assert.equal(checkDemoCredentials(DEMO_CREDENTIALS.customerNo, DEMO_CREDENTIALS.password), DEMO_CUSTOMER);
});

for (const [customerNo, password] of [
  [DEMO_CREDENTIALS.customerNo, '654321'],
  ['987654321', DEMO_CREDENTIALS.password],
  ['', ''],
  ['', DEMO_CREDENTIALS.password],
  [DEMO_CREDENTIALS.customerNo, ''],
  [' \t\n ', ''],
]) {
  test(`yanlış veya boş bilgiler null döndürür: ${JSON.stringify([customerNo, password])}`, () => {
    assert.equal(checkDemoCredentials(customerNo, password), null);
  });
}

test('müşteri numarasının başındaki ve sonundaki boşluklar kırpılır', () => {
  assert.equal(checkDemoCredentials(` \t${DEMO_CREDENTIALS.customerNo}\n `, DEMO_CREDENTIALS.password), DEMO_CUSTOMER);
});

for (const password of [` ${DEMO_CREDENTIALS.password}`, `${DEMO_CREDENTIALS.password} `, `\t${DEMO_CREDENTIALS.password}\n`]) {
  test(`şifrede boşluk kırpılmaz: ${JSON.stringify(password)}`, () => {
    assert.equal(checkDemoCredentials(DEMO_CREDENTIALS.customerNo, password), null);
  });
}

// Expected strings verified with Node's tr-TR Intl formatter, including code points;
// there is no space (ordinary or non-breaking) between the symbol and the amount.
for (const [kurus, expected] of [
  [1_245_075, '₺12.450,75'],
  [0, '₺0,00'],
  [5, '₺0,05'],
  [-1_245_075, '-₺12.450,75'],
  [123_456_789_012, '₺1.234.567.890,12'],
] as const) {
  test(`formatKurus ${kurus} kuruşu tam Türkçe para biçiminde gösterir`, () => {
    assert.equal(formatKurus(kurus), expected);
  });
}

test('goalProgress normal oranı döndürür', () => {
  assert.equal(goalProgress(3_820_000, 5_000_000), 0.764);
});

test('goalProgress hedefi aşan bakiyeyi 1 ile sınırlar', () => {
  assert.equal(goalProgress(6_000_000, 5_000_000), 1);
});

test('goalProgress negatif bakiyeyi 0 ile sınırlar', () => {
  assert.equal(goalProgress(-100, 5_000_000), 0);
});

test('goalProgress sıfır hedef için 1 döndürür', () => {
  assert.equal(goalProgress(100, 0), 1);
  assert.equal(goalProgress(0, 0), 1);
});

test('demo müşterisinin numarası giriş bilgileriyle tutarlıdır', () => {
  assert.equal(DEMO_CUSTOMER.customerNo, DEMO_CREDENTIALS.customerNo);
});

test('demo hesaplarının tutarları tam sayı kuruştur', () => {
  assert.ok(DEMO_CUSTOMER.accounts.length > 0);
  for (const account of DEMO_CUSTOMER.accounts) {
    assert.ok(Number.isSafeInteger(account.balanceKurus), `${account.id}: balanceKurus`);
    if (account.goalKurus !== undefined) {
      assert.ok(Number.isSafeInteger(account.goalKurus), `${account.id}: goalKurus`);
    }
  }
});

test('demo hesaplarının kimlikleri benzersizdir', () => {
  const ids = DEMO_CUSTOMER.accounts.map((account) => account.id);
  assert.equal(new Set(ids).size, ids.length);
});
