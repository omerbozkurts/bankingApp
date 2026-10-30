// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

import { ageOn, formatDateInput, parseTrDate, validateRegister } from './validation.ts';

const TODAY = new Date(2026, 9, 28); // 28.10.2026
const OK = {
  nationalId: '10000000146',
  fullName: 'Ayşe Demir',
  birthDate: '20.05.1995',
  password: '482913',
  passwordRepeat: '482913',
};

test('geçerli kayıt formu hatasızdır', () => {
  assert.deepEqual(validateRegister(OK, TODAY), {});
});

test('tarih biçimlendirme ve okuma', () => {
  assert.equal(formatDateInput('20051995'), '20.05.1995');
  assert.equal(formatDateInput('2005'), '20.05');
  assert.equal(parseTrDate('20.05.1995'), '1995-05-20');
  assert.equal(parseTrDate('29.02.2023'), null);
  assert.equal(parseTrDate('29.02.2024'), '2024-02-29');
  assert.equal(parseTrDate('2005.1995'), null);
});

test('yaş doğum gününe göre hesaplanır', () => {
  assert.equal(ageOn('2008-10-28', TODAY), 18);
  assert.equal(ageOn('2008-10-29', TODAY), 17);
});

test('18 yaş altı ve gelecek tarih reddedilir', () => {
  assert.match(validateRegister({ ...OK, birthDate: '29.10.2008' }, TODAY).birthDate!, /18 yaşından/);
  assert.equal(validateRegister({ ...OK, birthDate: '28.10.2008' }, TODAY).birthDate, undefined);
  assert.equal(validateRegister({ ...OK, birthDate: '01.01.2030' }, TODAY).birthDate, 'Doğum tarihi geçersiz.');
});

test('geçersiz T.C., isim ve şifreler reddedilir', () => {
  const e = validateRegister(
    { nationalId: '12345678901', fullName: 'Ay5e', birthDate: '20.05.1995', password: '123456', passwordRepeat: '654321' },
    TODAY,
  );
  assert.equal(e.nationalId, 'T.C. kimlik numarası geçersiz.');
  assert.equal(e.fullName, 'Ad soyad yalnızca harflerden oluşmalı.');
  assert.match(e.password!, /Tahmin edilmesi kolay/);
  assert.equal(e.passwordRepeat, 'Şifreler eşleşmiyor.');
});

test('kolay şifreler: tekrar eden ve ardışık rakamlar', () => {
  for (const password of ['111111', '000000', '123456', '654321', '345678']) {
    assert.ok(validateRegister({ ...OK, password, passwordRepeat: password }, TODAY).password, password);
  }
});

test('ardışık olmayan şifreler kabul edilir (backend ile aynı kural)', () => {
  for (const password of ['789876', '898765', '482913']) {
    assert.equal(validateRegister({ ...OK, password, passwordRepeat: password }, TODAY).password, undefined, password);
  }
});
