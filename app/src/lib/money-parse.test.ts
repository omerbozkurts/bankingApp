// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

import { parseTryAmount } from './money.ts';

for (const [input, expected] of [
  ['250', 25_000],
  ['250,5', 25_050],
  ['250,05', 25_005],
  ['1.234,56', 123_456],
  ['1.500', 150_000],
  ['1.234.567', 123_456_700],
  ['12.5', 1_250],
  ['₺ 1.000,00', 100_000],
  ['100 TL', 10_000],
  ['0,01', 1],
  ['007', 700],
] as const) {
  test(`parseTryAmount(${JSON.stringify(input)}) = ${expected}`, () => {
    assert.equal(parseTryAmount(input), expected);
  });
}

for (const input of ['', '0', '0,00', '-5', 'abc', '1,234', '1,2,3', '12.345,6.7', '1e5', '1.23.4']) {
  test(`parseTryAmount(${JSON.stringify(input)}) geçersizdir`, () => {
    assert.equal(parseTryAmount(input), null);
  });
}

test('çok büyük tutarlar reddedilir', () => {
  assert.equal(parseTryAmount('1234567890123'), null);
});
