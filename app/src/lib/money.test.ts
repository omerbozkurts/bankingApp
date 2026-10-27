// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

// @ts-ignore -- Node's native TypeScript runner requires the .ts extension.
import { formatKurus, goalProgress } from './money.ts';

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
