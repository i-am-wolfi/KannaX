# nikgapps via SourceForge (feed RSS de arquivos, sem Cloudflare)

"""links do NikGapps direto do SourceForge. Ex: ,nikgapps 16 core"""

import asyncio
import difflib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import requests

from kannax import Message, kannax

_UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}
_SF = "https://sourceforge.net/projects/nikgapps"
_RSS = f"{_SF}/rss"
_FILES = f"{_SF}/files/Releases"
_CHANNEL = "https://t.me/NikGapps"
_CACHE_TTL = 6 * 3600
_MIN_VER, _MAX_VER = 11, 18
# Releases/Android-16/22-Feb-2026/NikGapps-core-arm64-16-20260222-signed.zip
_MAIN_RE = re.compile(
    r"^Releases/Android-(\d+)/([^/]+)/NikGapps-([a-z]+)-arm64-\1-(\d{8})-signed\.zip$"
)
# Releases/Android-16/22-Feb-2026/Addons/NikGapps-Addon-16-YouTube-20260222-signed.zip
_ADDON_RE = re.compile(
    r"^Releases/Android-(\d+)/([^/]+)/Addons/NikGapps-Addon-\1-(.+)-(\d{8})-signed\.zip$"
)
_VARIANTS = ["Core", "Basic", "Omni", "Stock", "Full", "Go"]
# apelidos de outras famílias de gapps -> variante do NikGapps
_ALIAS = {"pico": "core", "nano": "core", "micro": "basic", "mini": "basic"}
_ADDON_WORDS = {"addons", "addon", "add-ons", "adons", "mods"}


# ---------- fonte de dados ----------
def _parse_links(xml: str) -> list:
    """caminhos relativos (Releases/...) dos arquivos listados no feed"""
    out = []
    for link in re.findall(r"<link>([^<]+)</link>", xml):
        link = link.strip()
        if "/projects/nikgapps/files/" not in link:
            continue
        rel = link.split("/projects/nikgapps/files/", 1)[1]
        if rel.endswith("/download"):
            rel = rel[: -len("/download")]
        if rel.startswith("Releases/"):
            out.append(rel)
    return out


def _fetch_rss(path: str) -> list:
    resp = requests.get(_RSS, params={"path": path}, headers=_UA, timeout=60)
    if resp.status_code == 404:
        return []  # pasta não existe (versão sem releases)
    resp.raise_for_status()
    return _parse_links(resp.text)


def _scan() -> dict:
    """{ver: {date, main, addons, addon_date, addon_latest}} de todas as versões"""
    vers = [str(v) for v in range(_MIN_VER, _MAX_VER + 1)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        pages = list(ex.map(lambda v: (v, _fetch_rss(f"/Releases/Android-{v}")), vers))
    versions = {}
    for ver, items in pages:
        if not items:
            continue  # pasta não existe (ex.: Android-17)
        mains, addons, dates = {}, {}, []
        for rel in items:
            m = _MAIN_RE.match(rel)
            if m:
                ymd, date = m.group(4), m.group(2)
                cur = mains.get(m.group(3).capitalize())
                if not cur or ymd >= cur[0]:
                    mains[m.group(3).capitalize()] = (
                        ymd, date, f"{_SF}/files/{rel}/download",
                    )
                dates.append((ymd, date))
                continue
            m = _ADDON_RE.match(rel)
            if m:
                ymd, date = m.group(4), m.group(2)
                cur = addons.get(m.group(3))
                if not cur or ymd >= cur[0]:
                    addons[m.group(3)] = (ymd, date, f"{_SF}/files/{rel}/download")
                dates.append((ymd, date))
        if not dates:
            continue
        # o feed é limitado a ~100 itens: os zips principais de versões
        # antigas podem ter ficado de fora — refina olhando a pasta da data
        if not mains:
            for rel in _fetch_rss(f"/Releases/Android-{ver}/{max(dates)[1]}"):
                m = _MAIN_RE.match(rel)
                if m:
                    mains[m.group(3).capitalize()] = (
                        m.group(4), m.group(2), f"{_SF}/files/{rel}/download",
                    )
        main_ymd = max((y for y, _, _ in mains.values()), default="")
        main_date = next((d for y, d, _ in mains.values() if y == main_ymd), max(dates)[1])
        addon_ymd = max((y for y, _, _ in addons.values()), default="")
        addon_latest = next((d for y, d, _ in addons.values() if y == addon_ymd), "")
        versions[ver] = {
            "date": main_date,  # data dos pacotes principais
            "main": {v: u for v, (_, _, u) in mains.items()},
            "addons": {n: u for n, (_, _, u) in addons.items()},
            "addon_date": {n: d for n, (_, d, _) in addons.items()},
            "addon_latest": addon_latest,
        }
    return versions


def _cache_path() -> str:
    from kannax import Config

    cache_dir = os.path.join(
        getattr(Config, "DOWN_PATH", "downloads/"), ".nikgapps_cache"
    )
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "releases.json")


def _load() -> dict:
    path = _cache_path()
    if os.path.isfile(path) and time.time() - os.path.getmtime(path) < _CACHE_TTL:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    data = _scan()
    if data:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass
    return data


# ---------- mensagens ----------
def _norm_var(want: str) -> str:
    w = want.strip().lower()
    w = _ALIAS.get(w, w)
    for v in _VARIANTS:
        if w == v.lower():
            return v
    close = difflib.get_close_matches(w, [v.lower() for v in _VARIANTS], n=1, cutoff=0.6)
    if close:
        for v in _VARIANTS:
            if v.lower() == close[0]:
                return v
    return ""


def _match_addon(info: dict, want: str):
    addons = info.get("addons") or {}
    low = {k.lower(): k for k in addons}
    w = want.strip().lower()
    if w in low:
        return low[w]
    for k, orig in low.items():
        if w in k:
            return orig
    close = difflib.get_close_matches(w, low.keys(), n=1, cutoff=0.5)
    if close:
        return low[close[0]]
    return ""


def _msg_help(data: dict) -> str:
    vers = sorted(data, key=int, reverse=True)
    lines = ["📦 **NikGapps** — releases no SourceForge\n"]
    for ver in vers:
        lines.append(
            f"• **Android {ver}** (`{data[ver]['date']}`) → `,nikgapps {ver}`"
        )
    lines += [
        "\nVariantes: " + " | ".join(_VARIANTS) + " (Pico = Core)",
        "➕ Addons: `,nikgapps 16 addons` — ou um app: `,nikgapps 16 youtube`",
        f"📂 [Todas as releases]({_FILES}/)",
        f"💬 [Canal {_CHANNEL.split('/')[-1]}]({_CHANNEL})",
    ]
    return "\n".join(lines)


def _msg_variants(ver: str, info: dict) -> str:
    folder = f"{_FILES}/Android-{ver}/{info['date']}/"
    mains = info.get("main") or {}
    lines = [f"📦 **NikGapps — Android {ver}** (`{info['date']}`)\n"]
    for v in _VARIANTS:
        if v in mains:
            lines.append(f"• [{v}]({mains[v]})")
    for v in sorted(mains):
        if v not in _VARIANTS:
            lines.append(f"• [{v}]({mains[v]})")
    if not mains:
        lines.append("`Nenhum pacote principal encontrado (só addons nessa versão).`")
    lines += [
        f"\n➕ {len(info.get('addons') or {})} addons → `,nikgapps {ver} addons`",
        f"📂 [Pasta da release]({folder})",
    ]
    return "\n".join(lines)


def _msg_one(ver: str, info: dict, var: str) -> str:
    link = (info.get("main") or {}).get(var)
    if not link:
        have = ", ".join(sorted(info.get("main") or {})) or "nenhuma"
        return (
            f"`NikGapps {var} para Android {ver} não existe.`\n"
            f"Disponíveis: {have}"
        )
    return (
        f"📦 **NikGapps {var} — Android {ver}** (`{info['date']}`)\n\n"
        f"⬇️ [Baixar {var} arm64]({link})\n"
        f"📂 [Pasta da release]({_FILES}/Android-{ver}/{info['date']}/)\n"
        f"💬 [Canal @NikGapps]({_CHANNEL})"
    )


def _msg_addons(ver: str, info: dict) -> str:
    addons = info.get("addons") or {}
    if not addons:
        return f"`Nenhum addon para Android {ver}.`"
    date = info.get("addon_latest") or info.get("date") or ""
    lines = [f"➕ **NikGapps Addons — Android {ver}** (`{date}`)", ""]
    size, shown = len(lines[0]), 0
    for name in sorted(addons, key=str.lower):
        line = f"• [{name}]({addons[name]})"
        if size + len(line) + 1 > 3800:  # limite do Telegram é 4096
            lines.append(f"`… e mais {len(addons) - shown} addons.`")
            break
        lines.append(line)
        size += len(line) + 1
        shown += 1
    lines += [
        "",
        f"📂 [Pasta de addons]({_FILES}/Android-{ver}/{date}/Addons/)",
        f"💬 [Canal @NikGapps]({_CHANNEL})",
    ]
    return "\n".join(lines)


def _msg_addon_one(ver: str, info: dict, name: str) -> str:
    addons = info.get("addons") or {}
    date = (info.get("addon_date") or {}).get(name) or info.get("date") or ""
    return (
        f"➕ **NikGapps Addon {name} — Android {ver}** (`{date}`)\n\n"
        f"⬇️ [Baixar {name}]({addons[name]})\n"
        f"📂 [Pasta de addons]({_FILES}/Android-{ver}/{date}/Addons/)"
    )


# ---------- comando ----------
async def _run(message: Message):
    args = (message.input_str or "").strip().split()
    await message.edit("`Lendo releases do NikGapps...`")
    data = await asyncio.to_thread(_load)
    if not data:
        await message.edit(
            "`Não consegui ler as releases do SourceForge agora. Tente de novo.`",
            del_in=10,
        )
        return
    vers = sorted(data, key=int, reverse=True)
    latest = vers[0]

    ver = next((a for a in args if a.isdigit() and a in data), None)
    bad_ver = next((a for a in args if a.isdigit() and a not in data), None)
    rest = [a for a in args if a != ver]
    want = " ".join(rest).strip()

    if bad_ver:
        await message.edit(
            f"`Não achei Android {bad_ver} no NikGapps.`\n"
            f"Disponíveis: {', '.join(vers)}",
            del_in=15,
        )
        return

    if not ver:
        # sem versão: addons/variante usam a mais recente
        if want.lower() in _ADDON_WORDS:
            await message.edit(_msg_addons(latest, data[latest]), disable_web_page_preview=True)
            return
        if want:
            var = _norm_var(want)
            if var:
                await message.edit(_msg_one(latest, data[latest], var), disable_web_page_preview=True)
                return
            name = _match_addon(data[latest], want)
            if name:
                await message.edit(
                    _msg_addon_one(latest, data[latest], name), disable_web_page_preview=True
                )
                return
        await message.edit(_msg_help(data), disable_web_page_preview=True)
        return

    info = data[ver]
    if not want:
        await message.edit(_msg_variants(ver, info), disable_web_page_preview=True)
        return
    if want.lower() in _ADDON_WORDS:
        await message.edit(_msg_addons(ver, info), disable_web_page_preview=True)
        return
    var = _norm_var(want)
    if var and var in (info.get("main") or {}):
        await message.edit(_msg_one(ver, info, var), disable_web_page_preview=True)
        return
    if var and (info.get("main") or {}):
        await message.edit(_msg_one(ver, info, var), disable_web_page_preview=True)
        return
    name = _match_addon(info, want)
    if name:
        await message.edit(_msg_addon_one(ver, info, name), disable_web_page_preview=True)
        return
    await message.edit(
        f"`Nada para '{want}' no Android {ver}.`\n"
        f"Variantes: {', '.join(_VARIANTS)}\n"
        f"Addons: `,nikgapps {ver} addons`",
        del_in=15,
    )


@kannax.on_cmd(
    "nikgapps",
    about={
        "header": "NikGapps (SourceForge)",
        "description": "Links reais do NikGapps por versão do Android, variante e addons.",
        "usage": "{tr}nikgapps [android] [variante|addon]  (ex: {tr}nikgapps 16 core)",
    },
)
async def nikgapps_(message: Message):
    """nikgapps releases from sourceforge"""
    await _run(message)


@kannax.on_cmd(
    "ngapps",
    about={
        "header": "NikGapps (SourceForge)",
        "description": "Alias de nikgapps: links reais do NikGapps por Android/variante/addon.",
        "usage": "{tr}ngapps [android] [variante|addon]  (ex: {tr}ngapps 16 core)",
    },
)
async def ngapps_(message: Message):
    """nikgapps releases from sourceforge (alias)"""
    await _run(message)
