"""Instagram resmi Content Publishing API'si (Reels).

Akis Meta'nin sartlarina birebir uyar:
  1) POST /{ig-user-id}/media          -> container olustur (media_type=REELS)
  2) GET  /{container-id}?fields=status_code -> FINISHED olana kadar bekle
  3) POST /{ig-user-id}/media_publish  -> yayinla

Meta videoyu kendi indirdigi icin 2. adim dakikalar surebilir; asenkron
bir isi senkron beklemek yerine ustel araliklarla yoklariz.
"""
import time

import requests

from . import log

# Meta'nin container durum kodlari
TERMINAL_OK = {"FINISHED"}
TERMINAL_BAD = {"ERROR", "EXPIRED"}


class InstagramError(RuntimeError):
    pass


def _explain(resp: requests.Response) -> str:
    try:
        err = resp.json().get("error", {})
    except ValueError:
        return f"HTTP {resp.status_code}: {resp.text[:250]}"
    msg = err.get("message", "?")
    code = err.get("code")
    sub = err.get("error_subcode")
    hint = _hint(code, sub, msg)
    return f"HTTP {resp.status_code} code={code} subcode={sub}: {msg}{hint}"


def _hint(code, sub, msg: str) -> str:
    m = (msg or "").lower()
    if code == 190:
        return ("\n  -> Token gecersiz/suresi dolmus. Uzun omurlu token 60 gunde biter; "
                "refresh-token is akisinin calistigini kontrol edin.")
    if code == 200 or "permission" in m:
        return ("\n  -> Izin eksik. Uygulamanizda instagram_business_content_publish "
                "(ve instagram_business_basic) izinleri onayli olmali.")
    if code == 9 or "limit" in m:
        return "\n  -> 24 saatlik yayin kotasi (50 gonderi) dolmus olabilir."
    if "media_type" in m or "aspect" in m:
        return "\n  -> Video 9:16, 5-90sn, H.264 + AAC olmali."
    if "url" in m or "fetch" in m or "download" in m:
        return ("\n  -> Meta video_url'i indiremedi. Adres public mi, "
                "Content-Type video/mp4 mi, yonlendirme calisiyor mu?")
    return ""


class Instagram:
    def __init__(self, cfg):
        self.cfg = cfg
        self.base = cfg.graph_base
        self.session = requests.Session()

    def _post(self, path: str, data: dict) -> dict:
        data = {**data, "access_token": self.cfg.ig_token}
        r = self.session.post(f"{self.base}/{path}", data=data, timeout=180)
        if r.status_code != 200:
            raise InstagramError(f"POST {path} -> {_explain(r)}")
        return r.json()

    def _get(self, path: str, params: dict) -> dict:
        params = {**params, "access_token": self.cfg.ig_token}
        r = self.session.get(f"{self.base}/{path}", params=params, timeout=120)
        if r.status_code != 200:
            raise InstagramError(f"GET {path} -> {_explain(r)}")
        return r.json()

    # -- tanilama ------------------------------------------------------------
    def whoami(self) -> dict:
        return self._get(self.cfg.ig_user_id, {"fields": "id,username,account_type"})

    def quota(self) -> dict:
        try:
            data = self._get(f"{self.cfg.ig_user_id}/content_publishing_limit",
                             {"fields": "config,quota_usage"})
            return (data.get("data") or [{}])[0]
        except InstagramError as exc:
            log.warn(f"kota sorgulanamadi (kritik degil): {exc}")
            return {}

    # -- yayinlama -----------------------------------------------------------
    def create_container(self, video_url: str, caption: str) -> str:
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption[:2200],
            "share_to_feed": "true" if self.cfg.share_to_feed else "false",
        }
        data = self._post(f"{self.cfg.ig_user_id}/media", payload)
        cid = data.get("id")
        if not cid:
            raise InstagramError(f"container id donmedi: {data}")
        log.info(f"container olusturuldu: {cid}")
        return cid

    def wait_ready(self, container_id: str, *, timeout_s: int = 900) -> None:
        deadline = time.time() + timeout_s
        delay = 5
        last = None
        while time.time() < deadline:
            data = self._get(container_id, {"fields": "status_code,status"})
            code = data.get("status_code")
            if code != last:
                log.info(f"container durumu: {code} ({data.get('status', '')[:120]})")
                last = code
            if code in TERMINAL_OK:
                return
            if code in TERMINAL_BAD:
                raise InstagramError(
                    f"container {code}: {data.get('status')}"
                    f"{_hint(None, None, str(data.get('status')))}"
                )
            time.sleep(delay)
            delay = min(30, int(delay * 1.4))
        raise InstagramError(f"container {timeout_s}sn icinde hazir olmadi (son durum: {last})")

    def publish(self, container_id: str) -> dict:
        data = self._post(f"{self.cfg.ig_user_id}/media_publish",
                          {"creation_id": container_id})
        media_id = data.get("id")
        if not media_id:
            raise InstagramError(f"media id donmedi: {data}")
        info = {"id": media_id}
        try:
            info |= self._get(media_id, {"fields": "permalink,media_type,timestamp"})
        except InstagramError as exc:
            log.warn(f"permalink alinamadi (gonderi yine de yayinlandi): {exc}")
        return info

    def post_reel(self, video_url: str, caption: str) -> dict:
        cid = self.create_container(video_url, caption)
        self.wait_ready(cid)
        return self.publish(cid)


def refresh_long_lived_token(cfg) -> dict:
    """60 gunluk tokeni yeniler. Haftalik is akisi bunu cagirir."""
    if cfg.ig_flavor == "instagram":
        url = "https://graph.instagram.com/refresh_access_token"
        params = {"grant_type": "ig_refresh_token", "access_token": cfg.ig_token}
    else:
        raise InstagramError(
            "Facebook Login akisinda token yenileme app secret gerektirir; "
            "IG_API_FLAVOR=instagram kullanmanizi oneririm."
        )
    r = requests.get(url, params=params, timeout=60)
    if r.status_code != 200:
        raise InstagramError(f"token yenilenemedi -> {_explain(r)}")
    return r.json()
