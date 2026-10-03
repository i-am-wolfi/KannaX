# Copyright (C) 2020 BY - GitHub.com/code-rgb [TG - @deleteduser420]
# All rights reserved.

import datetime
import time

import requests

from kannax import Message, kannax

API_HOST = "https://api.orangefox.download/v3"


def _api_get(path: str, params: dict | None = None, tries: int = 3) -> dict:
    """GET with retries (FoxAPI flakes out intermittently)."""
    last = None
    for i in range(tries):
        try:
            resp = requests.get(f"{API_HOST}{path}", params=params, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"OrangeFox API falhou após {tries} tentativas: {last}")


def _human_size(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{num} {unit}"
        num /= 1024
    return f"{num:.1f} GB"


def _find_device(codename: str) -> dict | None:
    devs = _api_get("/devices").get("data", [])
    codename = codename.strip().lower()
    exact, partial = [], []
    for d in devs:
        names = [d.get("codename", "")] + list(d.get("codenames") or [])
        names = [n.lower() for n in names if n]
        if codename in names:
            exact.append(d)
        elif any(codename in n or n in codename for n in names):
            partial.append(d)
    return (exact or partial or [None])[0]


def _release_of_type(device_id: str, want: str) -> tuple:
    """(release or None, available types). Prefers active, falls back to archived."""
    rels = _api_get("/releases", params={"device_id": device_id}).get("data", [])
    rels = [r for r in rels if r.get("device_id") == device_id]
    if not rels:
        return None, []
    types = sorted({r.get("type", "?") for r in rels})
    pool = [r for r in rels if r.get("type") == want]
    if not pool:
        return None, types
    active = [r for r in pool if not r.get("archived")] or pool
    return max(active, key=lambda r: r.get("date", 0)), types


@kannax.on_cmd(
    "ofox",
    about={
        "header": "get orangefox recovery by device codename do"
        ".ofox codename [stable|beta] (works in inline too)"
    },
)
async def ofox_(message: Message):
    if not message.input_str:
        await message.err("Provide a device codename to search recovery", del_in=2)
        return
    codename = message.input_str.strip().split()[0]
    want = "stable"
    parts = message.input_str.strip().split()
    if len(parts) > 1 and parts[-1].lower() in ("stable", "beta"):
        want = parts[-1].lower()
        codename = parts[0]
    await message.edit("🔍 searching for recovery...", del_in=2)
    photo = "https://i.imgur.com/582uaSk.png"
    try:
        dev = _find_device(codename)
    except Exception as e:
        await message.err(f"OrangeFox API error: `{e}`", del_in=5)
        return
    if not dev:
        await message.err(f"recovery not found for {codename}!", del_in=3)
        return
    try:
        s, available = _release_of_type(dev["id"], want)
    except Exception as e:
        await message.err(f"OrangeFox API error: `{e}`", del_in=5)
        return
    if not s:
        await message.err(
            f"no {want} releases for {dev.get('full_name', codename)}! "
            f"(disponível: {', '.join(available) or 'nada'})",
            del_in=5,
        )
        return
    maintainer = (dev.get("maintainer") or {}).get("name", "?")
    date = datetime.datetime.fromtimestamp(s.get("date", 0)).strftime("%Y-%m-%d")
    changelog = s.get("changelog") or []
    clog = "\n".join(f"• {c}" for c in changelog[:10])
    info = f"📱 **Device**: {dev.get('full_name', codename)}\n"
    info += f"👤 **Maintainer**: {maintainer}\n\n"
    recovery = f"🦊 <code>{s.get('filename', '?')}</code>\n"
    recovery += f"📅 {date}\n"
    recovery += f"ℹ️ **Version:** {s.get('version', '?')}\n"
    recovery += f"📌 **Build Type:** {s.get('type', '?')}\n"
    recovery += f"🔰 **Size:** {_human_size(s.get('size', 0))}\n\n"
    if clog:
        recovery += "📍 **Changelog:**\n"
        recovery += f"<code>{clog}</code>\n\n"
    msg = info + recovery
    notes_ = s.get("notes")
    if notes_:
        try:
            from html_telegraph_poster import TelegraphPoster
            t = TelegraphPoster(use_api=True)
            t.create_api_token("KannaX")
            notes = t.post(title="READ Notes", author="", text=str(notes_))
            msg += f"🗒️ <a href={notes['url']}>NOTES</a>\n"
        except Exception:
            pass
    dl = s.get("url") or ""
    if not dl and isinstance(s.get("mirrors"), list) and s["mirrors"]:
        dl = s["mirrors"][0].get("url", "")
    msg += f"⬇️ <a href={dl}>DOWNLOAD</a>"
    await kannax.send_photo(message.chat.id, photo=photo, caption=msg)
