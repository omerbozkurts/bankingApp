// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

import { formatIban, isValidNationalId, isValidTrIban, normalizeIban } from './banking.ts';

// Same IBANs the backend seeds (backend/scripts/seed_demo.py) plus a real-format sample.
const VALID = ['TR809999900000000000000001', 'TR269999900000000000000003', 'TR330006100519786457841326'];

for (const iban of VALID) {
  test(`geçerli IBAN: ${iban}`, () => {
    assert.equal(isValidTrIban(iban), true);
    assert.equal(isValidTrIban(formatIban(iban).toLowerCase()), true);
  });
}

test('tek hanesi değişen IBAN geçersizdir', () => {
  const broken = VALID[0].slice(0, -1) + '2';
  assert.equal(isValidTrIban(broken), false);
});

test('yanlış uzunluk, ülke kodu veya rezerv hanesi geçersizdir', () => {
  assert.equal(isValidTrIban('TR80999990000000000000001'), false);
  assert.equal(isValidTrIban('DE89370400440532013000'), false);
  assert.equal(isValidTrIban('TR809999910000000000000001'), false);
  assert.equal(isValidTrIban(''), false);
});

test('normalizeIban boşlukları siler ve büyük harfe çevirir', () => {
  assert.equal(normalizeIban(' tr80 9999 9000 0000 0000 0000 01 '), VALID[0]);
});

test('formatIban dörtlü gruplar oluşturur', () => {
  assert.equal(formatIban(VALID[0]), 'TR80 9999 9000 0000 0000 0000 01');
  assert.equal(formatIban('TR8099'), 'TR80 99');
});

test('T.C. kimlik no doğrulaması', () => {
  assert.equal(isValidNationalId('10000000146'), true);
  assert.equal(isValidNationalId('10000000147'), false);
  assert.equal(isValidNationalId('01000000146'), false);
  assert.equal(isValidNationalId('1000000014'), false);
  assert.equal(isValidNationalId('100000001460'), false);
  assert.equal(isValidNationalId('1000000014a'), false);
});
