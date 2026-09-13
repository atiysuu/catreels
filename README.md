# catreels — otonom kedi sitcom'u

Her gün 20:00'de kendi kendine bir bölüm yazar, çeker ve Instagram'a Reel
olarak yükler. GitHub Actions üzerinde çalışır; bilgisayarın kapalı olabilir.

```
Gemini            seedream-5-pro        minimax-h3            ffmpeg           Graph API
bölüm senaryosu → açılış karesi     →   15 sn animasyon   →   kurgu + ses  →   yayın
                  (Release'e yüklenir)   (start_frame ile)
```

**Maliyet:** ~0,35 $/bölüm → günde 1 yayınla **~10,50 $/ay**.

---

## Dizi

Sabit kadro, sabit ev. Espri karakterden çıkıyor: Pasha'nın tembelliğini
bilince kanepe sahnesinde ne yapacağını tahmin edip gülüyorsun.

| | |
|---|---|
| **Pasha** | Kanepenin kendini atamış kralı. Tembel, gururlu, her aksiliği kişisel hakaret sayar |
| **Mochi** | Evi toplayan endişeli olan. Erken ve sık panikler |
| **Olive** | Olayları başlatan dolapçı. Planı hep geri teper |
| **Biscuit** | Her şeyi yiyen sessiz ev arkadaşı. En kötü anda belirir |

Kadro `src/cast.py`'de. Karakter tarifi modelden gelmiyor — her bölümde
birebir aynı metin isteme giriyor. Diziyi dizi yapan şey bu.

---

## Neden bu mimari

Üç şey deneyerek bulundu, üçü de sayıyla doğrulandı.

### Açılış karesi (image-to-video)

Başta saf text-to-video kullanılıyordu: modelden aynı anda kedileri çizmesi,
odayı kurması **ve** hareketi oynatması isteniyordu. Karakterler kayıyor,
sahneler birbirine giriyordu.

Araştırma bunun mimari bir sınır olduğunu söylüyor — image-to-video'da
modelin tek işi hareket kaldığı için çıktı öngörülebilir oluyor. Ölçümle de
doğrulandı: başlangıç karesi verilen testte kedi kalktı, bardağa yürüdü,
devirdi ve kenardan aşağı baktı; aynı istem karesiz verildiğinde model
hiçbir şeyi oynatmadı.

> Açılış karesi **public** bir adreste olmalı — video servisi onu kendi
> indiriyor. `gen.pollinations.ai` adresi kimlik istediği için doğrudan
> verilemiyor (401); bu yüzden kare GitHub Release'e yükleniyor.

### Düz istem

Stil blokları, kamera notları ve "not CGI" listeleri içeren mühendislik
istemi, insan gibi yazılmış sade bir istemle karşılaştırıldı. **Düz istem
açık ara kazandı** — model kısa cümleleri daha iyi oynatıyor, uzun teknik
metin onu boğuyor.

Yoğun karakter tarifi artık yalnızca **açılış karesinde** kullanılıyor;
orada detay işe yarıyor.

### Az sahne, büyük olay

Sahne başına düşen süre iki kez yükseltildi, ikisi de gözlemle:

| sn/sahne | 15 sn'de | Sonuç |
|---|---|---|
| 2,0 | 7 sahne | Birbirine giriyordu |
| 4,0 | 3 sahne | Hâlâ bozuluyordu |
| **7,0** | **2 sahne** | Temiz |

Olay sayısını artırmak yerine olayın kendisini büyütmek daha iyi sonuç
veriyor: bir tatmin edici devrilme, yarım görünen dört taneden iyi.

---

## Servis durumları (ölçülmüş)

| Servis | Durum |
|---|---|
| Gemini metin | ✅ ücretsiz — `gemini-flash-latest` zincirin başında |
| Gemini Pro | ❌ ücretsiz katmanda yok (429), faturalandırma ister |
| `gen.pollinations.ai` görsel | ✅ gerçek yüksek çözünürlük (seedream 1504×2672) |
| `image.pollinations.ai` | ⚠️ **model parametresini yok sayıyor** — hep 576×1024, filigranlı |
| Kling 3.0 | ❌ Pollinations'ta yok; fal.ai'de ayda 27–40 $ |

Denenip bırakılanlar: **Veo 3.1 Fast** (görüntüsü daha iyi ama 8 saniyede
ya durgun ya karmakarışık, ayda 24 $), **seedance-2.5** (ayda 18,50 $,
480p), **ücretsiz flux + ffmpeg** (slayt görünümü).

---

## Kurulum

Secrets → [Settings → Secrets → Actions](../../settings/secrets/actions):

| Secret | Zorunlu | Ne için |
|---|---|---|
| `IG_ACCESS_TOKEN` | ✅ | Instagram yayını |
| `GEMINI_API_KEY` | ✅ | Bölüm senaryosu |
| `POLLINATIONS_API_KEY` | ✅ | Açılış karesi + video (Pollen bakiyesi gerekir) |
| `GH_PAT` | önerilir | Token yenileme (izin: Secrets → Read and write) |

`GITHUB_TOKEN` otomatik gelir. Depo **public** olmalı: Instagram videoyu
Release linkinden indiriyor.

Kontrol:

```bash
python scripts/doctor.py        # tüm bağımlılıklar ve anahtarlar
python -m src.main --check      # sadece Instagram bağlantısı
```

---

## Kullanım

```bash
python -m src.main --dry-run              # üret, yayınlama
python scripts/produce.py --clips 1 --episode 12 --name test
python scripts/publish_file.py --video manual/x.mp4 --caption manual/x.txt
```

Actions'tan elle: **Gunluk Reel** (üretir + yayınlar) veya
**Hazir videoyu yayinla** (repodaki bir mp4'ü yayınlar, Pollen harcamaz).

---

## Ayarlar

`src/config.py` tek doğruluk kaynağı. `.env` yalnızca sırları taşır —
oraya ayar yazmak kod güncellemelerini sessizce ezer, daha önce iki kez
yaşandı (ölü Gemini modeli ve eski `REEL_SHOTS`).

| Değişken | Varsayılan | Etkisi |
|---|---|---|
| `VIDEO_MODEL` | `minimax/minimax-h3-max-turbo` | Takma adı yok, tam ad şart |
| `VIDEO_RESOLUTION` | `1080p` | 480p 0,00625 / 768p 0,01 / 1080p 0,02 $/sn |
| `VIDEO_CLIP_SECONDS` | `15` | Model **yalnızca** 5/10/15 kabul eder |
| `REEL_SHOTS` | `3` | Senaryo vuruşu; videoda ilk ve son kullanılır |
| `KEYFRAME_MODEL` | `seedream-5-pro` | Açılış karesi |
| `USE_KEYFRAME` | `1` | Kapatılırsa saf text-to-video |
| `VIDEO_BACKEND` | `pollinations` | Bakiye biterse otomatik `free`'ye düşer |

---

## Bilinen tuzaklar

**Bakiye bitince sessizce ücretsiz yola düşer.** Yayın durmaz ama slayt
görünümlü video yayınlanır. 9 Eylül'de bakiye 3. klibe yetmeyince bölüm
12 yerine 8 saniye çıktı.

**Token 60 günde ölür.** `refresh-token.yml` haftalık yeniler ve bitiş
tarihini `state/token_expiry.json`'a yazar; günlük çalışma 14 günden az
kalınca uyarır. `GH_PAT` yoksa secret otomatik güncellenmez.

**Yükleme sonrası CDN gecikmesi.** Asset Release'e çıktıktan sonra
yayılması birkaç saniye sürüyor; `verify()` bu yüzden 5 kez deniyor.
Tek denemeyken bir yayın tamamen düşmüştü.

**GitHub 60 gün hareketsiz depoda cron'u durdurur.** Günlük iş akışı
`state/history.json` commit'lediği için depo aktif kalır.

---

## Dosya düzeni

```
src/
  main.py        uçtan uca akış
  cast.py        sabit kadro ve ev
  ideas.py       bölüm senaryosu + düz istem kurucusu
  keyframe.py    açılış karesi üretimi ve yayınlanması
  textgen.py     Gemini zinciri -> Pollinations -> yerel şablon
  backends/
    ai_video.py    image-to-video (Pollen harcar)
    free_motion.py görsel + ffmpeg hareketi (bedava yedek)
  assemble.py    ffmpeg kurgu, kanca metni, kodlama
  audio.py       model sesi + müzik + efekt karışımı
  host.py        Release'e yükleme ve public doğrulama
  instagram.py   Graph API yayını
```
