// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

import {
  formatIsoDate,
  presetRange,
  rangeDays,
  rangeError,
  statementFilename,
  turkishDateFormatter,
  turkishToday,
  withBom,
  // @ts-ignore -- Node's native TypeScript runner requires the .ts extension.
} from './statement.ts';

// 22:30 UTC on 31 October is already 1 November in Turkey.
const LATE_OCTOBER = new Date('2026-10-31T22:30:00Z');

test('turkishToday Türkiye saatine göre günü verir', () => {
  assert.equal(turkishToday(LATE_OCTOBER), '2026-11-01');
  assert.equal(turkishToday(new Date('2026-10-31T20:59:00Z')), '2026-10-31');
});

test('presetRange bu ay, son 30 ve son 90 günü hesaplar', () => {
  assert.deepEqual(presetRange('thisMonth', LATE_OCTOBER), { from: '2026-11-01', to: '2026-11-01' });
  assert.deepEqual(presetRange('last30', LATE_OCTOBER), { from: '2026-10-03', to: '2026-11-01' });
  assert.deepEqual(presetRange('last90', LATE_OCTOBER), { from: '2026-08-04', to: '2026-11-01' });
  assert.equal(rangeDays(presetRange('last30', LATE_OCTOBER)), 30);
  assert.equal(rangeDays(presetRange('last90', LATE_OCTOBER)), 90);
});

test('rangeError ters ve çok uzun aralıkları yakalar', () => {
  assert.equal(rangeError({ from: '2026-11-01', to: '2026-11-01' }), null);
  assert.match(rangeError({ from: '2026-11-02', to: '2026-11-01' })!, /sonra olamaz/);
  assert.equal(rangeError({ from: '2025-01-01', to: '2026-01-01' }), null);
  assert.match(rangeError({ from: '2025-01-01', to: '2026-01-02' })!, /366/);
});

test('statementFilename ve formatIsoDate', () => {
  assert.equal(
    statementFilename('TR960000000000000000001234', { from: '2026-11-01', to: '2026-11-30' }),
    'ABBank-ekstre-1234-20261101-20261130.csv',
  );
  assert.equal(formatIsoDate('2026-11-01'), '01.11.2026');
});

test('rangeError artık yılda 366 günü kabul eder, 367 günü reddeder (API ile aynı)', () => {
  assert.equal(rangeDays({ from: '2024-01-01', to: '2024-12-31' }), 366);
  assert.equal(rangeError({ from: '2024-01-01', to: '2024-12-31' }), null);
  assert.match(rangeError({ from: '2024-01-01', to: '2025-01-01' })!, /366/);
});

test('withBom baştaki BOM işaretini tek sefer ekler', () => {
  assert.equal(withBom('a;b'), '\uFEFFa;b');
  assert.equal(withBom('\uFEFFa;b'), '\uFEFFa;b');
});

test('turkishDateFormatter saati Türkiye saatiyle gösterir', () => {
  const format = turkishDateFormatter({ hour: '2-digit', minute: '2-digit' });
  assert.equal(format.format(new Date('2026-10-31T21:30:00Z')), '00:30');
});
