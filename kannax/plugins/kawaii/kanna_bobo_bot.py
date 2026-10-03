# device specs via GSM Arena (no bot needed)

"""puxa ficha de celular direto do gsmarena.com"""

import asyncio
import re

import requests
from bs4 import BeautifulSoup

from kannax import Message, kannax

_UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}
_SPEC_RE = re.compile(r"^https?://(?:www|m)\.gsmarena\.com/[a-z0-9_\-]+-\d+\.php$")
_SKIP_RE = re.compile(r"-(pictures|review|price|vs_|compare)")


def _search_models(query: str, limit: int = 6) -> list:
    """Find GSM Arena spec page URLs via DuckDuckGo site: search."""
    resp = requests.post(
        "https://html.duckduckgo.com/html/",
        data={"q": f"site:gsmarena.com {query} Full phone specifications"},
        headers=_UA,
        timeout=30,
    )
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    found = []
    for a in soup.select("a.result__a"):
        href = a.get("href", "")
        title = a.get_text(" ", strip=True)
        if _SPEC_RE.match(href) and not _SKIP_RE.search(href) and href not in found:
            name = re.sub(r"\s*-\s*Full phone specifications.*$", "", title).strip()
            found.append((name or href, href))
        if len(found) >= limit:
            break
    return found


def _get_spec(url: str, row: str) -> str:
    """First matching spec row text for a section title."""
    try:
        resp = requests.get(url, headers=_UA, timeout=30)
        resp.raise_for_status()
    except Exception:
        return ""
    soup = BeautifulSoup(resp.content, "html.parser")
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""
    cur_sec, picked, specs = "", {}, {}
    for tr in soup.select("#specs-list tr"):
        th = tr.find("th")
        if th:
            cur_sec = th.get_text(strip=True)
            continue
        ttl = tr.find("td", class_="ttl")
        nfo = tr.find("td", class_="nfo")
        if ttl and nfo:
            key = (cur_sec, ttl.get_text(strip=True))
            if key not in picked:
                picked[key] = nfo.get_text(" ", strip=True)
                specs.setdefault(cur_sec, []).append(
                    (ttl.get_text(strip=True), nfo.get_text(" ", strip=True))
                )
    if row == "name":
        return name
    if row == "all":
        return specs  # type: ignore[return-value]
    sec, ttl = row.split("|", 1)
    return picked.get((sec, ttl), "")


def _fmt_specs(name: str, url: str, specs: dict) -> str:
    def g(sec, ttl):
        for t, v in specs.get(sec, []):
            if t == ttl:
                return v
        return ""

    def first(sec, skip=("Features", "Video")):
        for t, v in specs.get(sec, []):
            if t not in skip and v:
                return v
        rows = specs.get(sec, [])
        return rows[0][1] if rows else ""

    res = g("Display", "Resolution").split(",")[0]
    rows = [
        ("🖥 Tela", " | ".join(v for v in (g("Display", "Size").split(",")[0], g("Display", "Type"), res) if v)),
        ("⚙ Chip", g("Platform", "Chipset")),
        ("🧠 RAM/ROM", g("Memory", "Internal")),
        ("📷 Traseira", g("Main Camera", "Triple") or g("Main Camera", "Dual") or g("Main Camera", "Single") or g("Main Camera", "Quad") or first("Main Camera")),
        ("🤳 Frontal", g("Selfie camera", "Single") or first("Selfie camera")),
        ("🔋 Bateria", g("Battery", "Type") or first("Battery", skip=())),
        ("📏 Corpo", " | ".join(v for v in (g("Body", "Dimensions"), g("Body", "Weight")) if v)),
        ("📅 Lançado", " | ".join(v for v in (g("Launch", "Announced"), g("Launch", "Status")) if v)),
        ("🎨 Cores", g("Misc", "Colors")),
    ]
    lines = [f"📱 **{name}**", ""]
    lines += [f"**{label}:** {val}" for label, val in rows if val]
    lines += ["", f"🔗 [Ficha completa]({url})"]
    return "\n".join(lines)


@kannax.on_cmd(
    "d",
    about={
        "header": "Ficha de celular (GSM Arena)",
        "description": "Busca as especificações de um dispositivo no gsmarena.com.",
        "usage": "{tr}d [dispositivo]",
    },
)
async def gsm_device(message: Message):
    """device specs from gsm arena"""
    query = (message.input_str or "").strip()
    if not query:
        await message.edit("`Forneça um dispositivo. Ex: ,d Redmi Note 12`", del_in=5)
        return
    await message.edit(f"`Buscando {query} no GSM Arena...`")
    try:
        models = await asyncio.to_thread(_search_models, query)
    except Exception as e:
        await message.edit(f"`Busca falhou: {e}`", del_in=10)
        return
    if not models:
        await message.edit(f"`Nada encontrado para {query}. Tente outro nome.`", del_in=10)
        return
    name, url = models[0]
    try:
        specs = await asyncio.to_thread(_get_spec, url, "all")
        title = await asyncio.to_thread(_get_spec, url, "name")
    except Exception as e:
        await message.edit(f"`Falha lendo a ficha: {e}`", del_in=10)
        return
    text = _fmt_specs(title or name, url, specs)
    if len(models) > 1:
        others = "\n".join(f"• {n}" for n, _ in models[1:4])
        text += f"\n\n**Também achei:**\n{others}\nRefine a busca se não for esse."
    await message.edit(text, disable_web_page_preview=True)
