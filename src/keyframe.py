"""Bolumun ACILIS KARESINI uretir ve public bir adrese koyar.

Neden var
---------
Bu ana kadar hat saf text-to-video calisiyordu: video modelinden ayni anda
kedileri cizmesi, odayi kurmasi, isigi ayarlamasi VE hareketi oynatmasi
isteniyordu. Modelden yapabileceginin en zorunu istemek buydu; karakterlerin
kaymasi ve sahnelerin birbirine girmesi buradan geliyordu.

Arastirma da bunu soyluyor: image-to-video, karakter tutarliliginda
text-to-video'ya gore MIMARI olarak ustun, cunku modelin tek isi hareket
kaliyor. Olcumle de dogrulandi -- baslangic karesi verilen 5 saniyelik
testte kedi kalkti, bardaga yurudu, devirdi ve kenardan asagi bakti; ayni
istem karesiz verildiginde model hicbir seyi oynatmiyordu.

Iki tuzak
---------
* Eski `image.pollinations.ai` ucu model parametresini YOK SAYIYOR: uc
  farkli model istendiginde uc dosya da ayni md5'i donduruyor ve hepsi
  576x1024 ile sinirli. Kaliteli kare icin `gen.pollinations.ai/image/`
  kullanilmali -- orada seedream-5-pro 1504x2672 veriyor.
* Video servisi kareyi KENDISI indiriyor, dolayisiyla adres kimlik
  dogrulamasiz erisilebilir olmali. gen ucunun URL'i dogrudan verilemez
  (401 -> "Failed to download the file"), bu yuzden kare once uretilip
  GitHub Release'e yukleniyor.
"""
import pathlib
import urllib.parse

import requests

from . import cast, log
from .pollinations import GEN_BASE, PollinationsError

# Ucretsiz uctaki filigran video'ya miras kaliyor; bu yuzden acilis karesi
# her zaman ucretli bir modelden alinir.
DEFAULT_MODEL = "seedream-5-pro"


def build_prompt(idea: dict, beat: dict) -> str:
    """Acilis karesinin istemi: ilk vurusun DONMUS hali.

    Video isteminin aksine burada DETAY ise yariyor: kare bir kez uretilip
    butun bolumun gorunumunu kilitliyor, dolayisiyla yogun karakter tarifi
    ve fotograf dili burada kaliyor. Duz isteme gecis yalnizca VIDEO
    tarafi icindi.
    """
    from .ideas import NO_TEXT
    return (
        f"{idea['character']} {beat['action']}. "
        f"Scene: {idea['setting']}. "
        f"{idea['style']}. Vertical 9:16 composition, all cats fully in frame, "
        f"sharp focus. {NO_TEXT}"
    )


def render(cfg, prompt: str, dest: pathlib.Path, *, seed: int) -> pathlib.Path:
    """Kaliteli acilis karesini uretip diske yazar."""
    # FLUX.2 Pro gibi bazi modeller 16'nin kati olmayan boyutu reddediyor;
    # 1088x1920 hem 16'ya bolunuyor hem 9:16'ya cok yakin.
    params = {
        "model": cfg.keyframe_model,
        "width": 1088,
        "height": 1920,
        "seed": seed,
        "nologo": "true",
    }
    url = (f"{GEN_BASE}/image/" + urllib.parse.quote(prompt, safe="")
           + "?" + urllib.parse.urlencode(params))
    headers = {"User-Agent": "catreels/1.0"}
    if cfg.pollinations_key:
        headers["Authorization"] = f"Bearer {cfg.pollinations_key}"

    r = requests.get(url, headers=headers, timeout=300)
    ctype = r.headers.get("content-type", "")
    if r.status_code != 200 or "image" not in ctype:
        raise PollinationsError(
            f"acilis karesi uretilemedi: HTTP {r.status_code} {ctype} "
            f"{r.text[:180] if 'json' in ctype else ''}"
        )
    dest.write_bytes(r.content)
    log.info(f"acilis karesi: {cfg.keyframe_model}, {len(r.content) // 1024}KB")
    return dest


def publish(cfg, path: pathlib.Path) -> str | None:
    """Kareyi public bir adrese koyar. Barindirma yoksa None doner.

    Video servisi kareyi kendisi indirdigi icin adres kimlik dogrulamasiz
    olmali. Yerelde GH_TOKEN olmadan bu yapilamaz; o durumda cagiran taraf
    karesiz (saf text-to-video) devam eder.
    """
    from . import host
    try:
        url = host.upload(cfg, path)
        host.verify_image(url)
        return url
    except host.HostError as exc:
        log.warn(f"acilis karesi yayinlanamadi ({exc}); "
                 f"bu bolum karesiz uretilecek")
        return None
