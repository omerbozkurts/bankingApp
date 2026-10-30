# AB Bank — API (FastAPI)

**Python 3.14 · FastAPI · SQLAlchemy 2.1 (async) · asyncpg · PostgreSQL 18 · Alembic · Argon2 (pwdlib) · JWT (PyJWT)**

## Kurulum

Gereksinimler: [uv](https://docs.astral.sh/uv/) ve Docker.

```bash
cd backend
cp .env.example .env          # JWT_SECRET'ı değiştirin (komut dosyanın içinde)
docker compose up -d --wait   # PostgreSQL 18 → 127.0.0.1:5434 (abbank + abbank_test)
uv sync                       # Python 3.14 ve bağımlılıklar
uv run alembic upgrade head   # şemayı oluştur
uv run python -m scripts.seed_demo   # demo: 123456789 / 123456 ve alıcı 987654321 / 654321
uv run fastapi dev app/main.py       # http://localhost:8000 — belgeler: /docs
```

## Uç noktalar

| Yöntem | Yol | Açıklama |
|---|---|---|
| `POST` | `/auth/register` | `{national_id, full_name, birth_date, password}` → `{customer_no}`; vadesiz hesap açılır |
| `POST` | `/auth/login` | `{customer_no, password}` → `{access_token, token_type, expires_in}` + web oturum çerezi |
| `POST` | `/auth/logout` | Web oturum çerezini siler |
| `GET` | `/me` | Giriş yapmış müşteri (Bearer token veya web çerezi) |
| `GET` | `/accounts` | Müşterinin hesapları; tutarlar **kuruş** cinsinden tam sayı |
| `POST` | `/accounts` | Yeni hesap (`checking` / `savings` + isteğe bağlı hedef / `credit`); geçerli TR IBAN üretilir |
| `GET` | `/accounts/{id}/transactions` | Hareketler, yeniden eskiye; `?limit=20&before_id=` ile sayfalama |
| `GET` | `/recipients/lookup?iban=` | Alıcının maskeli adı ("Al*** Ka***"), göndermeden önce onay için |
| `POST` | `/transfers` | Para transferi; `idempotency_key` aynı isteğin iki kez ödenmesini engeller |
| `GET` | `/health` | Uygulama ve veritabanı durumu |

## Güvenlik

- Şifreler **Argon2id** ile özetlenir; düz metin hiçbir yerde tutulmaz.
- Hatalı şifre, olmayan müşteri ve kilitli hesap **aynı yanıtı (401) ve aynı süreyi** alır; müşteri numarasının
  var olup olmadığı anlaşılmaz.
- Aynı müşteriye **5 hatalı denemeden sonra 15 dakika kilit**; ayrıca IP başına **5 dakikada 20 giriş denemesi**
  (`429`). Ayarlar `app/config.py`'de.
- **Mobil** istemci token'ı `Authorization: Bearer` ile gönderir. **Web** istemci httpOnly + Secure +
  SameSite=Strict çerez kullanır; çerezli isteklerde `X-Requested-With` başlığı zorunludur (CSRF koruması).
- Erişim token'ı 30 dakika geçerli; imza anahtarı `.env`'deki `JWT_SECRET` (en az 32 karakter, varsayılanı yok).
- Para tutarları `BigInteger` kuruş; negatif bakiye veritabanı kısıtıyla engellenir.
- **Transfer:** müşteri satırı kilitlenir (aynı müşterinin transferleri sıraya girer), iki hesap id sırasıyla
  `FOR UPDATE` kilitlenir (karşılıklı transferde deadlock olmaz), bakiye kilitli satırdan okunur. Limitler:
  işlem başına 50.000 TL, 24 saatte 100.000 TL; kendi hesaplar arası aktarım bu limitlere tabi değil ve
  günlük toplama sayılmaz. Aynı `idempotency_key` farklı içerikle gelirse `409`.
- **Kredili hesap:** müşteri başına bir tane, faizsiz döner limit (varsayılan 20.000 TL, `credit_limit_kurus`).
  Bakiye borcu gösterir (≤ 0) ve limitin altına inemez; bu kurallar veritabanı kısıtıyla da korunur. Yalnızca
  kendi hesaplar arasında kullanılır: limitten çekim ve borç kadar geri ödeme. Başka müşterinin kredili hesabı
  alıcı sorgusunda ve transferde bulunamaz sayılır.
- **Kayıt:** T.C. kimlik no algoritmik olarak doğrulanır ve düz metin saklanmaz; `NATIONAL_ID_PEPPER` ile
  HMAC özeti tutulur (kişi başına tek kayıt). 18 yaş sınırı, kolay şifre engeli, IP başına saatte 5 kayıt.
- Alıcı sorgusu müşteri başına 5 dakikada 30 ile sınırlı (maskeli isim toplanmasın diye).

## Geliştirme

```bash
uv run pytest -q              # testler (abbank_test veritabanında)
uv run ruff check .           # lint
uv run alembic revision --autogenerate -m "açıklama"   # model değişince yeni migration
```

> Not: Windows'ta async psycopg varsayılan olay döngüsüyle çalışmadığı için sürücü olarak asyncpg
> kullanılıyor. Üretimde PgBouncer (transaction modu) eklenirse bağlantıya
> `prepared_statement_cache_size=0` verilmelidir.
