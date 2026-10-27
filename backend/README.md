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
uv run python -m scripts.seed_demo   # demo müşteri: 123456789 / 123456
uv run fastapi dev app/main.py       # http://localhost:8000 — belgeler: /docs
```

## Uç noktalar

| Yöntem | Yol | Açıklama |
|---|---|---|
| `POST` | `/auth/login` | `{customer_no, password}` → `{access_token, token_type, expires_in}` |
| `GET` | `/me` | Giriş yapmış müşteri (Bearer token) |
| `GET` | `/accounts` | Müşterinin hesapları; tutarlar **kuruş** cinsinden tam sayı |
| `GET` | `/health` | Uygulama ve veritabanı durumu |

## Güvenlik

- Şifreler **Argon2id** ile özetlenir; düz metin hiçbir yerde tutulmaz.
- Hatalı şifre ve olmayan müşteri **aynı yanıtı ve aynı süreyi** alır (müşteri numarası tahmini zorlaşır).
- Aynı müşteriye **5 hatalı denemeden sonra 15 dakika kilit** (`429`). Ayarlar `app/config.py`'de.
- Erişim token'ı 30 dakika geçerli; imza anahtarı `.env`'deki `JWT_SECRET` (en az 32 karakter, varsayılanı yok).
- Para tutarları `BigInteger` kuruş; negatif bakiye veritabanı kısıtıyla engellenir.

## Geliştirme

```bash
uv run pytest -q              # testler (abbank_test veritabanında)
uv run ruff check .           # lint
uv run alembic revision --autogenerate -m "açıklama"   # model değişince yeni migration
```

> Not: Windows'ta async psycopg varsayılan olay döngüsüyle çalışmadığı için sürücü olarak asyncpg
> kullanılıyor. Üretimde PgBouncer (transaction modu) eklenirse bağlantıya
> `prepared_statement_cache_size=0` verilmelidir.
