# catreels — otonom AI kedi Reels botu

Her gün belirlenen saatlerde kendi kendine bir kedi konsepti uydurur, videoyu
üretir ve Instagram'a Reel olarak yükler. GitHub Actions üzerinde çalışır,
bilgisayarınızın açık olması gerekmez.

```
Gemini (ücretsiz)      Pollinations flux        ffmpeg              GitHub Release        Instagram Graph API
konsept + açıklama  →  kare görselleri      →  hareket + kurgu  →  public mp4 linki   →  Reel yayını
```

---

## Önce ücretsizlik gerçeği

Kurmadan önce bilmeniz gereken şey: **"Gemini ile ücretsiz AI video" diye bir
şey yok.** 1 Eylül 2026 itibarıyla canlı olarak doğruladım:

| Servis | Durum | Not |
|---|---|---|
| Gemini API — metin | ✅ ücretsiz | AI Studio anahtarı, kart istemiyor |
| Gemini API — Veo (video) | ❌ ücretli | Free tier yok, saniye başı ücret |
| Pollinations — flux görsel | ✅ ücretsiz, anahtarsız | 576×1024 ile sınırlı |
| Pollinations — metin | ❌ anonimde kapalı | 32 karakterlik istek bile HTTP 402 |
| Pollinations — video | ❌ ücretli | Tüm modeller `paid_only`, Pollen kredisi |

Bu yüzden proje iki video yolu ile geliyor:

**`VIDEO_BACKEND=free` (varsayılan, gerçekten bedava)**
Tek bir seed kilitlenip aynı kedi 7 farklı pozda üretilir, ffmpeg bunları
Ken Burns hareketi + geçişlerle akıcı bir videoya çevirir. Sınırsız çalışır.
Karakter tutarlılığı şaşırtıcı derecede iyi — aynı kedi, aynı papyon, her karede.

**`VIDEO_BACKEND=pollinations` (gerçek AI video, ücretli)**
Gerçekten hareket eden klipler. `wan-fast` ile 4 klip × 5 sn ≈ **0,20 Pollen
(~0,20 $)** — yani günde 1 Reel ≈ ayda ~6 $. Kredi biterse otomatik olarak
ücretsiz yola düşer, hat durmaz.

---

## Kurulum

### 1. Depoyu hazırlayın

```bash
git init && git add . && git commit -m "catreels" && git push
```

> Depo **public** olmalı: Instagram videoyu GitHub Release linkinden indirecek.
> Gizli kalması gerekiyorsa `HOST_MODE=r2` ile Cloudflare R2 kullanın.

### 2. Gemini anahtarı (ücretsiz)

[aistudio.google.com/apikey](https://aistudio.google.com/apikey) → Create API key.
Kredi kartı istemez. `gemini-2.5-flash` ücretsiz katmanda günde ~500 istek verir;
günde 3 Reel bunun binde biri.

### 3. Instagram tarafı

1. Instagram hesabınızı **Professional** (Business veya Creator) yapın.
2. [developers.facebook.com](https://developers.facebook.com) → yeni uygulama →
   **Instagram** ürününü ekleyin (*Instagram API with Instagram Login*).
3. İzinler: `instagram_business_basic` + `instagram_business_content_publish`.
4. Uzun ömürlü token ve Instagram user ID'yi alın.

> **App Review gerekmez.** Uygulama "Development" modundayken yalnızca
> uygulamada rolü olan hesaplar adına işlem yapabilir — kendi hesabınıza
> gönderi attığınız için bu tam olarak istediğiniz şey. Kendinizi uygulamaya
> admin/tester olarak ekleyin, yeterli. App Review ancak başkalarının
> hesaplarına yayın yapacaksanız gerekir.

Doğrulayın:

```bash
python -m src.main --check
```

Hesap adı ve 24 saatlik kota yazdırıyorsa bağlantı hazır.

Tüm kurulumu tek bakışta görmek için:

```bash
python scripts/doctor.py
```

ffmpeg, font, müzik, Gemini, Pollinations, Instagram ve barındırma —
her biri için OK / UYARI / EKSIK satırı basar.

### 4. Secrets

Depo → Settings → Secrets and variables → Actions:

| Secret | Zorunlu | Ne için |
|---|---|---|
| `GEMINI_API_KEY` | önerilir | Konsept ve açıklama üretimi |
| `IG_USER_ID` | ✅ | Instagram hesap kimliği |
| `IG_ACCESS_TOKEN` | ✅ | Uzun ömürlü token |
| `GH_PAT` | önerilir | Token yenileme (izin: Secrets → Read and write) |
| `POLLINATIONS_API_KEY` | hayır | Daha yüksek çözünürlük / ücretli video yolu |

`GITHUB_TOKEN` otomatik gelir, eklemenize gerek yok.

### 5. Müzik ekleyin — bunu atlamayın

`assets/music/` klasörüne 3-5 adet telifsiz mp3 koyun. Boş bırakırsanız
video **sessiz** çıkar ve sessiz Reel'ler algoritmada neredeyse hiç
dağıtılmaz. Pixabay Music veya YouTube Audio Library uygun kaynaklar.
Her çalışmada rastgele biri seçilir, `loudnorm` ile seviyesi eşitlenir.

---

## Kullanım

```bash
python -m src.main --dry-run     # üret, yayınlama (out/latest.mp4)
python -m src.main --check       # sadece Instagram bağlantısını dene
python -m src.main               # tam akış
python -m src.main --backend pollinations   # bu çalışma için ücretli yol
```

Actions sekmesinden **Gunluk Reel → Run workflow** ile elle de tetikleyebilirsiniz;
`dry_run` kutusu işaretliyken video artifact olarak iner, Instagram'a gitmez.

Varsayılan yayın saatleri (TR): **10:00, 15:00, 20:00**. Değiştirmek için
`.github/workflows/daily-reel.yml` içindeki cron satırlarını düzenleyin —
GitHub cron **UTC** çalışır, Türkiye UTC+3'tür.

---

## Bilmeniz gereken tuzaklar

**Token 60 günde ölür.** `refresh-token.yml` her pazartesi yeniler. `GH_PAT`
tanımlamazsanız yenileme yapılır ama secret güncellenemez ve iş akışı bilerek
kırmızı yanar — sessizce durmasındansa uyarması daha iyi.

**GitHub 60 gün hareketsiz depolarda zamanlanmış iş akışlarını durdurur.**
Günlük iş akışı `state/history.json` dosyasını commit'lediği için depo sürekli
aktif kalır; bu yan etki bilinçlidir.

**Görseller 576×1024 geliyor.** Anonim katmanın tavanı bu — ne istersen iste
aynısını veriyor. 1080×1920'ye lanczos + `cas` + `unsharp` zinciriyle
büyütülüyor; sonuç iyi ama native değil. Ücretsiz bir Pollinations anahtarı
bu sınırı büyük olasılıkla kaldırır ve tek satırlık kalite artışıdır.

**Zamanlanmış çalışmalar gecikebilir.** GitHub yoğunlukta cron'u 15+ dakika
öteleyebilir. Dakikası dakikasına yayın gerekiyorsa VPS'e taşıyın.

**Kota:** Instagram 24 saatte 50 gönderiye izin veriyor; günde 3 Reel çok rahat.

**İlk gönderilerde acele etmeyin.** Yeni bir hesapta günde 3 otomatik gönderiyle
başlamak yerine 1'e düşürüp birkaç hafta ısıtmak daha güvenli.

---

## Dosya düzeni

```
src/
  main.py           uçtan uca akış, --dry-run / --check
  ideas.py          kedi konsept üreticisi + yerel yedek havuzu
  textgen.py        Gemini → Pollinations → yerel şablon sırası
  pollinations.py   görsel/metin/video istemcisi, hız sınırı yönetimi
  backends/
    free_motion.py  seed kilitli görseller + ffmpeg hareketi
    ai_video.py     gerçek AI video klipleri (Pollen)
  assemble.py       ffmpeg: Ken Burns, geçişler, kanca metni, ses, kodlama
  host.py           GitHub Release / R2 / hazır URL + erişim doğrulama
  instagram.py      Graph API: container → durum → yayın
state/history.json  üretilen her Reel'in kaydı (tekrar önleme)
```

## Konu havuzunu değiştirmek

`src/ideas.py` içindeki `THEMES` sözlüğü. Şu an dört tema var: `dans`, `ask`,
`karikoca`, `arkadas`. Yeni satır eklemek yeterli — Gemini onu tam bir çekim
listesine genişletir.
