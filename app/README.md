# AB Bank — Uygulama (Expo)

iOS, Android ve Web için tek kod tabanı: **Expo SDK 58 · React Native · TypeScript · Expo Router**.

## Çalıştırma

Önce API'yi başlatın (bkz. [`../backend/README.md`](../backend/README.md)), sonra:

```bash
cd app
npm install
npx expo start        # QR kodu Expo Go ile okutun (telefon) veya w ile web'de açın
npm run web           # doğrudan web
```

### Telefonda deneme

Telefon `localhost` ile bilgisayara ulaşamaz. `app/.env.local` dosyasına bilgisayarın yerel ağ IP'sini yazın
ve API'yi ağa açık başlatın:

```bash
# app/.env.local
EXPO_PUBLIC_API_URL=http://192.168.1.20:8000

# backend/ içinde
uv run fastapi dev app/main.py --host 0.0.0.0
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
| `src/app/` | Ekranlar (Expo Router): `index` karşılama, `kayit` hesap açma, `giris`, `hesabim`, `hesap/[id]` hareketler, `gonder` para transferi, `aktar` hesaplarım arası, `hesap-ac` yeni hesap, `asistan` bankacılık asistanı, `yonetici/` yönetici paneli (müşteri arama, `musteri/[id]`, `kayitlar`) |
| `src/components/brand/` | `Logo` bileşeni (sembol / yatay / dikey); yazı izleri `logo/brand` ana dosyasından |
| `src/components/ui/` | `Screen`, `ScreenHeader`, `Button`, `TextField`, `ChoiceList`, `Notice`, `Summary` |
| `src/constants/theme.ts` | Marka renkleri, Manrope font adları, boşluk ve yarıçap ölçüleri |
| `src/lib/api.ts` | API istemcisi (zaman aşımı, Türkçe hata mesajları) |
| `src/lib/session.ts` | Oturum durumu: açılışta geri yükleme, giriş, yenileme, çıkış |
| `src/lib/token-store*.ts` | Mobil: token `expo-secure-store`'da · Web: httpOnly çerez (JS'te token yok) |
| `src/lib/` (diğer) | IBAN/T.C. doğrulama, Türkçe tutar okuma (`1.250,50` → kuruş), form kuralları, API → uygulama eşlemesi, kredi borcu / kullanılabilir limit |
| `assets/images/` | Uygulama ikonu, Android uyarlanabilir/tek renk ikon, açılış görseli, favicon |

Marka kuralları: [`../logo/brand/MARKA.md`](../logo/brand/MARKA.md)
