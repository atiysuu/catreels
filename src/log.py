"""Tek satirlik, GitHub Actions dostu loglama."""
import os
import sys
import time

# Turkce Windows konsolu cp1254 kullaniyor ve Turkce aciklamalardaki emoji
# yazdirmayi UnicodeEncodeError ile cokertiyor. CI (Linux) bundan etkilenmiyor,
# ama yerel --dry-run kosusu tam da videoyu urettikten sonra patliyordu.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

_T0 = time.time()
_GHA = os.getenv("GITHUB_ACTIONS") == "true"


def _emit(level: str, msg: str) -> None:
    el = time.time() - _T0
    sys.stdout.write(f"[{el:7.1f}s] {level:<5} {msg}\n")
    sys.stdout.flush()


def info(msg: str) -> None:
    _emit("INFO", msg)


def warn(msg: str) -> None:
    _emit("WARN", msg)
    if _GHA:
        print(f"::warning::{msg}", flush=True)


def error(msg: str) -> None:
    _emit("ERROR", msg)
    if _GHA:
        print(f"::error::{msg}", flush=True)


def group(title: str) -> None:
    if _GHA:
        print(f"::endgroup::", flush=True)
        print(f"::group::{title}", flush=True)
    _emit("STEP", f"=== {title} ===")


def summary(md: str) -> None:
    """GitHub Actions ozet sayfasina yazar; yerelde stdout'a duser."""
    path = os.getenv("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(md.rstrip() + "\n")
    else:
        print(md, flush=True)
