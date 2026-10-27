# AB Bank — Marka Kılavuzu

## 1. Hikaye: Yükseliş

> **Katman katman yükselin.**

Kimse zirveye tek adımda çıkmaz. Her maaş, her küçük birikim, her doğru karar bir katmandır.
Katmanlar üst üste geldikçe zemin sağlamlaşır ve insan yükselir. AB Bank bu yolculuğun
zeminidir: birikimi güvenle taşır, her yeni katmanı görünür kılar.

- **Misyon:** İnsanların birikimini adım adım, güvenle büyütmelerine yardım etmek.
- **Vaat:** Her katman sayılır; hiçbir birikim küçük değildir.
- **Değerler:** Güven · Sadelik · İstikrar · Sıcaklık
- **Ses tonu:** Sakin, net ve cesaretlendirici. Abartı ve jargon yok; kısa cümleler, somut sayılar.
  - ✓ "Bu ay 500 ₺ biriktirdiniz. Yeni bir katman eklendi."
  - ✗ "Finansal özgürlüğe giden yolda devrim niteliğinde bir adım attınız!"
- **Slogan:** *Katman katman yükselin.* (Alternatifler: *Birikimle yükselin.* · *Her katman sizi yukarı taşır.*)

## 2. Logo

**Fikir:** Üst üste biriken üç katman bir **A** silueti kurar; zirvedeki **mercan** katman, ufukta
doğan güneş gibi yükselişin kendisidir. Alttaki iki ayrık katman A'nın bacaklarıdır; ortadaki katman onları birleştiren zemindir.

**Yapı:** Tüm katmanlar aynı yükseklikte (44 birim), tam yuvarlak uçlu, aralarında 16 birim boşluk.
Genişlikler aşağıdan yukarıya daralır: 208 → 144 → 80. Sembol optik merkez için hafif yukarıdadır.

| Versiyon | Dosya | Ne zaman |
|---|---|---|
| Yatay (ana) | `ab-bank-horizontal.svg` | Varsayılan; açık zeminde başlıklar, belgeler |
| Yatay, koyu zemin | `ab-bank-horizontal-dark.svg` | Lacivert / koyu zeminler (uygulamanın koyu teması) |
| Dikey | `ab-bank-stacked.svg`, `-dark.svg` | Kare alanlar, karşılama ekranı, afiş |
| Sembol | `ab-bank-symbol.svg`, `-dark.svg` | Logo yazısız kullanılacaksa (avatar, damga) |
| Küçük boy sembol | `ab-bank-symbol-small.svg` | 32 px ve altı (daha kalın katman, daha geniş boşluk) |
| Uygulama ikonu | `icons/ab-bank-app-icon.svg`, `icons/icon-*.png` | Pencere / masaüstü / mobil ikon |
| Favicon | `icons/favicon.ico`, `icons/favicon.svg` | Tarayıcı sekmesi (lacivert kutu içinde; açık ve koyu sekmede görünür) |
| Tek renk | `*-black.svg`, `*-white.svg`, `*-navy.svg` | Tek renk baskı, damga, kabartma |

Koyu zeminde alt katmanlar ve yazı **beyaz** olur; zirve her zaman **mercan** kalır.

## 3. Boşluk alanı

Logonun her yanında en az **1 katman yüksekliği** kadar boş alan bırakın (yatay logoda bu,
yazının büyük harf yüksekliğinin yaklaşık yarısıdır). Boşluk logoyla birlikte ölçeklenir.

## 4. En küçük boyut

| Versiyon | Ekran | Baskı |
|---|---|---|
| Yatay logo | 96 px genişlik | 25 mm genişlik |
| Dikey logo | 64 px genişlik | 18 mm genişlik |
| Sembol | 32 px (altında `symbol-small` / favicon kullanın) | 6 mm |

## 5. Renk

| Ad | Rol | HEX | RGB | CMYK (yaklaşık) |
|---|---|---|---|---|
| **Gece Laciverti** | Ana renk: logo katmanları, yazı, butonlar, koyu zemin | `#0E2A47` | 14 · 42 · 71 | 80 · 41 · 0 · 72 |
| **Şafak Mercanı** | Yalnızca zirve katmanı ve "yükseliş" anları | `#FF6B4A` | 255 · 107 · 74 | 0 · 58 · 71 · 0 |
| Beyaz | Zemin, koyu zeminde logo ve yazı | `#FFFFFF` | 255 · 255 · 255 | 0 · 0 · 0 · 0 |

- **Mercan az kullanılır:** Zirve rengi bir ödüldür; hedefe ulaşıldı, birikim arttı gibi anlar için saklayın.
  Geniş alanlarda ve metin rengi olarak kullanmayın (beyaz üzerinde kontrastı 2,8:1, metin için yetersiz).
- **Erişilebilirlik:** Lacivert/beyaz 14:1, her boyutta metin için uygun. Butonlar lacivert zemin + beyaz yazı.
- **Neden mavi + sarı değil:** Yuvarlak çubuklu "A" formu parlak mavi/sarı ile birleşince tanınmış bir reklam
  platformunun logosunu çağrıştırıyordu; lacivert + mercan bu benzerliği ortadan kaldırır.
- **Onaylı logo/zemin eşleşmeleri:** Tam renk beyaz üzerinde · koyu versiyon (beyaz + mercan) lacivert üzerinde ·
  beyaz tek renk fotoğraf/koyu zemin üzerinde · siyah tek renk beyaz üzerinde.
- CMYK değerleri ekran renginden hesaplanmıştır; baskıdan önce matbaa provasıyla doğrulayın.

## 6. Tipografi

- **Logo yazısı:** Manrope — "AB" Bold, "Bank" Medium. Logodaki yazı çizgiye (outline) çevrilmiştir;
  logoyu asla klavyeyle yeniden yazmayın, SVG dosyasını kullanın.
- **Arayüz ve metin:** Manrope (başlık 700, metin 400–500). Yedek: `Segoe UI`, `system-ui`, sans-serif.
- **Lisans:** Manrope, SIL Open Font License 1.1 ile lisanslıdır; ticari ve logo kullanımı serbesttir.

## 7. Grafik dil

Katman, markanın yapı taşıdır ve logonun dışında da kullanılabilir:
- **İlerleme göstergeleri:** Birikim hedefleri, üst üste dolan yuvarlak katmanlar olarak gösterilir;
  hedefe ulaşıldığında en üst katman mercan olur.
- **Köşe yarıçapı:** Arayüz öğelerinde tam yuvarlak (pill) butonlar ve 12 px kartlar.
- **Desen:** Logodaki katman ritmi (44 / 16) arka plan deseni olarak tekrar edilebilir; düşük kontrastta kullanın.

## 8. Yapılmaması gerekenler

Esnetmeyin veya sıkıştırmayın · katmanların sırasını, sayısını veya renklerini değiştirmeyin ·
zirve katmanını lacivert, alt katmanları mercan yapmayın · döndürmeyin veya ters çevirmeyin ·
gölge, kontur, gradyan veya efekt eklemeyin · logo parçalarının birbirine göre boyutunu değiştirmeyin ·
kalabalık fotoğrafların üzerine zemin olmadan koymayın.

## 9. Dosyalar

- `logo/brand/` — son ana dosyalar (SVG), `renders/` önizlemeler, `icons/` ikon seti
- `logo/brand/presentation.html` ve `slides/` — sunum panosu ve kullanım örnekleri
- `logo/concepts/` — keşif aşamasındaki tüm konseptler (arşiv)

> Not: Logonun tescil edilebilirliği garanti değildir. Ticari kullanımdan önce profesyonel bir marka
> araştırması (TÜRKPATENT veritabanı, tersine görsel arama) yaptırın.
