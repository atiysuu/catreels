"""Videoyu Instagram'in cekebilecegi PUBLIC bir adrese koyar.

Meta, video_url'i kendi sunucusundan indirir; bu yuzden adres kimlik
dogrulamasiz erisilebilir olmak zorunda. Uc secenek:
  release -> GitHub Release asset (ek kurulum yok, GITHUB_TOKEN yeter)
  r2      -> Cloudflare R2 public bucket (en saglami, yonlendirme yok)
  url     -> PUBLIC_VIDEO_URL ile hazir link verirsiniz
"""
import os
import pathlib

import requests

from . import log

GH_API = "https://api.github.com"
GH_UPLOAD = "https://uploads.github.com"


class HostError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# GitHub Release
# ---------------------------------------------------------------------------

def _gh_headers(cfg) -> dict:
    return {
        "Authorization": f"Bearer {cfg.gh_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _ensure_release(cfg) -> dict:
    url = f"{GH_API}/repos/{cfg.gh_repo}/releases/tags/{cfg.release_tag}"
    r = requests.get(url, headers=_gh_headers(cfg), timeout=60)
    if r.status_code == 200:
        return r.json()
    if r.status_code != 404:
        raise HostError(f"release sorgulanamadi: HTTP {r.status_code} {r.text[:200]}")

    log.info(f"'{cfg.release_tag}' release'i yok, olusturuluyor")
    r = requests.post(
        f"{GH_API}/repos/{cfg.gh_repo}/releases",
        headers=_gh_headers(cfg),
        json={
            "tag_name": cfg.release_tag,
            "name": "Reel deposu",
            "body": "Instagram'a gonderilen videolarin public barinagi. Otomatik olusturuldu.",
            "draft": False,
            "prerelease": False,
        },
        timeout=60,
    )
    if r.status_code not in (200, 201):
        raise HostError(f"release olusturulamadi: HTTP {r.status_code} {r.text[:300]}")
    return r.json()


def _delete_existing_asset(cfg, release: dict, name: str) -> None:
    for asset in release.get("assets", []):
        if asset.get("name") == name:
            requests.delete(f"{GH_API}/repos/{cfg.gh_repo}/releases/assets/{asset['id']}",
                            headers=_gh_headers(cfg), timeout=60)
            log.info(f"ayni adli eski asset silindi: {name}")


def _prune_release_assets(cfg, keep: int) -> None:
    """Eski videolari siler; her gun 3 Reel = yilda ~1000 asset birikmesin.

    Yayinlanmis bir Reel'in Instagram'daki kopyasi kalicidir; buradaki mp4
    yalnizca Meta'nin indirmesi icin gecici bir barinaktir.
    """
    r = requests.get(f"{GH_API}/repos/{cfg.gh_repo}/releases/tags/{cfg.release_tag}",
                     headers=_gh_headers(cfg), timeout=60)
    if r.status_code != 200:
        return
    assets = sorted(r.json().get("assets", []),
                    key=lambda a: a.get("created_at", ""), reverse=True)
    for asset in assets[keep:]:
        resp = requests.delete(
            f"{GH_API}/repos/{cfg.gh_repo}/releases/assets/{asset['id']}",
            headers=_gh_headers(cfg), timeout=60)
        if resp.status_code in (200, 204):
            log.info(f"eski asset temizlendi: {asset['name']}")


def _upload_release(cfg, path: pathlib.Path) -> str:
    release = _ensure_release(cfg)
    name = path.name
    _delete_existing_asset(cfg, release, name)

    headers = _gh_headers(cfg) | {"Content-Type": "video/mp4"}
    with path.open("rb") as fh:
        r = requests.post(
            f"{GH_UPLOAD}/repos/{cfg.gh_repo}/releases/{release['id']}/assets",
            headers=headers, params={"name": name}, data=fh, timeout=900,
        )
    if r.status_code not in (200, 201):
        raise HostError(f"asset yuklenemedi: HTTP {r.status_code} {r.text[:300]}")
    return r.json()["browser_download_url"]


# ---------------------------------------------------------------------------
# Cloudflare R2
# ---------------------------------------------------------------------------

def _upload_r2(cfg, path: pathlib.Path) -> str:
    try:
        import boto3
    except ImportError as exc:
        raise HostError("R2 icin boto3 gerekli: pip install boto3") from exc

    client = boto3.client(
        "s3",
        endpoint_url=cfg.r2_endpoint,
        aws_access_key_id=cfg.r2_access_key,
        aws_secret_access_key=cfg.r2_secret_key,
        region_name="auto",
    )
    key = f"reels/{path.name}"
    client.upload_file(str(path), cfg.r2_bucket, key,
                       ExtraArgs={"ContentType": "video/mp4"})
    return f"{cfg.r2_public_base.rstrip('/')}/{key}"


# ---------------------------------------------------------------------------

def upload(cfg, path: pathlib.Path) -> str:
    mode = cfg.host_mode
    log.info(f"public barindirma modu: {mode}")
    if mode == "release":
        url = _upload_release(cfg, path)
        try:
            _prune_release_assets(cfg, keep=cfg.keep_assets)
        except requests.RequestException as exc:
            log.warn(f"eski asset temizligi atlandi: {exc}")
    elif mode == "r2":
        url = _upload_r2(cfg, path)
    elif mode == "url":
        url = (os.getenv("PUBLIC_VIDEO_URL") or "").strip()
        if not url:
            raise HostError("HOST_MODE=url secildi ama PUBLIC_VIDEO_URL bos")
    else:
        raise HostError(f"bilinmeyen HOST_MODE: {mode}")

    log.info(f"public URL: {url}")
    return url


def verify(url: str) -> None:
    """Meta indirmeden once biz indirelim: erisim ve icerik tipi dogru mu?

    GitHub Release adresleri imzali bir CDN adresine 302 atar; Meta bunu
    takip eder, biz de takip ederek ayni yolu dogrularız.
    """
    r = requests.get(url, stream=True, timeout=120, allow_redirects=True)
    ctype = r.headers.get("content-type", "")
    clen = r.headers.get("content-length", "?")
    head = next(r.iter_content(chunk_size=12), b"")
    r.close()

    if r.status_code != 200:
        raise HostError(f"public URL erisilemez: HTTP {r.status_code} ({url})")
    # MP4 dosyalari 4. bayttan itibaren 'ftyp' tasir.
    if b"ftyp" not in head:
        raise HostError(f"public URL bir MP4 dondurmuyor (ctype={ctype}, ilk baytlar={head!r})")

    log.info(f"public URL dogrulandi: HTTP 200, {ctype}, {clen} bayt")
