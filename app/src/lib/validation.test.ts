// @ts-ignore -- Node 24 provides this module; the app has no Node type declarations.
import { test } from 'node:test';
// @ts-ignore -- Node 24 provides this module; no extra dependency is needed to run it.
import assert from 'node:assert/strict';

// @ts-ignore -- Node's native TypeScript runner requires the .ts extension.
import { digitsOnly, validateLogin } from './validation.ts';

test('boş girişte iki alanın tam Türkçe mesajını döndürür', () => {
  assert.deepEqual(validateLogin('', ''), {
    customerNo: 'Müşteri numaranızı girin.',
    password: 'Şifrenizi girin.',
  });
});

test('yalnızca boşluk içeren müşteri numarası boştur', () => {
  assert.deepEqual(validateLogin(' \t\n ', '123456'), {
    customerNo: 'Müşteri numaranızı girin.',
  });
});

for (const customerNo of ['12345678', '1234567890', '1234a6789']) {
  test(`müşteri numarası yanlış biçim: ${customerNo}`, () => {
    assert.deepEqual(validateLogin(customerNo, '123456'), {
      customerNo: 'Müşteri numarası 9 haneli olmalı.',
    });
  });
}

test('9 haneli müşteri numarası ve 6 haneli şifre geçerlidir', () => {
  assert.deepEqual(validateLogin('123456789', '123456'), {});
});

test('müşteri numarasının başındaki ve sonundaki boşluklar kırpılır', () => {
  assert.deepEqual(validateLogin(' \t123456789\n ', '123456'), {});
});

test('baştaki sıfırlar geçerli hane olarak korunur', () => {
  assert.deepEqual(validateLogin('000000001', '000001'), {});
});

test('boş şifre için tam Türkçe mesajı döndürür', () => {
  assert.deepEqual(validateLogin('123456789', ''), {
    password: 'Şifrenizi girin.',
  });
});

for (const password of ['12345', '1234567', '12a456', '      ', ' 123456 ', '12345\n']) {
  test(`şifre tam 6 rakam olmalı: ${JSON.stringify(password)}`, () => {
    assert.deepEqual(validateLogin('123456789', password), {
      password: 'Şifre 6 haneli olmalı.',
    });
  });
}

test('iki alanın biçim hatalarını birlikte döndürür', () => {
  assert.deepEqual(validateLogin('abc', 'abcdef'), {
    customerNo: 'Müşteri numarası 9 haneli olmalı.',
    password: 'Şifre 6 haneli olmalı.',
  });
});

test('digitsOnly boş girdiyi korur', () => {
  assert.equal(digitsOnly('', 9), '');
});

test('digitsOnly rakamsız girdiyi boşaltır', () => {
  assert.equal(digitsOnly(' abc çş! \t\n', 9), '');
});

test('digitsOnly karışık girdide rakam dışını atar', () => {
  assert.equal(digitsOnly('a0 1-2ç3!4\n5', 9), '012345');
});

test('digitsOnly temizledikten sonra uzunluğu keser', () => {
  assert.equal(digitsOnly('a1 b2-c3 d4e5f6g7h8i9j0', 6), '123456');
});

test('digitsOnly sınırdaki rakamları değiştirmez', () => {
  assert.equal(digitsOnly('012345678', 9), '012345678');
});

test('digitsOnly sıfır uzunlukta boş sonuç döndürür', () => {
  assert.equal(digitsOnly('123456', 0), '');
});
