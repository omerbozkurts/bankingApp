# AB Bank

> Katman katman yükselin.

Birikimi adım adım büyütmek için sade ve güven veren bir bankacılık uygulaması.
Masaüstü (customtkinter) sürümünden mobil ve web'e taşınıyor.

## Yapı

| Klasör | İçerik |
|---|---|
| [`app/`](app/) | Yeni uygulama — Expo / React Native (iOS, Android, Web) |
| `backend/` | *(sıradaki adım)* FastAPI + PostgreSQL API |
| [`logo/`](logo/) | Marka kimliği: logo, ikonlar, sunum ve [marka kılavuzu](logo/brand/MARKA.md) |
| [`legacy/`](legacy/) | Eski masaüstü uygulaması (Python, customtkinter) — arşiv |

## Teknoloji

- **Uygulama:** Expo SDK 58, React Native, TypeScript, Expo Router, react-native-svg, Manrope
- **Sunucu (planlanan):** FastAPI, PostgreSQL, Argon2 şifre özeti, JWT oturum, Decimal para tutarları

## Eski masaüstü uygulaması

```bash
cd legacy
python tk.py
```

Gereksinim: `pip install customtkinter`. Eski sürüm şifreleri SHA-256 ile saklar ve verileri `.txt`
dosyalarında tutar; yeni sunucuda bunların yerini Argon2 ve PostgreSQL alacak.
