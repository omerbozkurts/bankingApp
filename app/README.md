# AB Bank — Uygulama (Expo)

iOS, Android ve Web için tek kod tabanı: **Expo SDK 58 · React Native · TypeScript · Expo Router**.

## Çalıştırma

```bash
cd app
npm install
npx expo start        # QR kodu Expo Go ile okutun (telefon) veya w ile web'de açın
npm run web           # doğrudan web
```

## Kontroller

```bash
npx tsc --noEmit      # tip denetimi
npx expo lint         # lint
npm test              # birim testleri (Node yerleşik test koşucusu)
npx expo export --platform web   # statik web çıktısı → dist/
```

## Yapı

| Yol | İçerik |
|---|---|
| `src/app/` | Ekranlar (Expo Router): `index` karşılama, `giris` giriş |
| `src/components/brand/` | `Logo` bileşeni (sembol / yatay / dikey); yazı izleri `logo/brand` ana dosyasından |
| `src/components/ui/` | `Button`, `TextField` |
| `src/constants/theme.ts` | Marka renkleri, Manrope font adları, boşluk ve yarıçap ölçüleri |
| `src/lib/` | Platformdan bağımsız mantık (doğrulama) |
| `assets/images/` | Uygulama ikonu, Android uyarlanabilir/tek renk ikon, açılış görseli, favicon |

Marka kuralları: [`../logo/brand/MARKA.md`](../logo/brand/MARKA.md)
