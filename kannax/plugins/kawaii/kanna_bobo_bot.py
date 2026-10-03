# device specs via GSM Arena (no bot needed)

"""puxa ficha de celular direto do gsmarena.com"""

import asyncio
import os
import re

import requests
from bs4 import BeautifulSoup

from kannax import Message, kannax

_UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}
_SITEMAP_URL = "https://www.gsmarena.com/sitemaps/phones.xml"
_SITEMAP_TTL = 7 * 24 * 3600  # refresh weekly


def _norm(text: str) -> list:
    return [t for t in re.sub(r"[^a-z0-9]+", " ", text.lower()).split() if t]


def _slug_name(url: str) -> str:
    slug = url.rsplit("/", 1)[1][:-4]
    slug = re.sub(r"-\d+$", "", slug)
    return slug.replace("_", " ")


def _sitemap_path() -> str:
    from kannax import Config

    cache_dir = os.path.join(getattr(Config, "DOWN_PATH", "downloads/"), ".gsm_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "phones.xml")


def _load_index() -> list:
    """(name, url) for every GSM Arena phone, cached from phones.xml."""
    import time

    path = _sitemap_path()
    fresh = os.path.isfile(path) and (time.time() - os.path.getmtime(path) < _SITEMAP_TTL)
    if not fresh:
        resp = requests.get(_SITEMAP_URL, headers=_UA, timeout=120)
        resp.raise_for_status()
        with open(path, "wb") as f:
            f.write(resp.content)
    with open(path, encoding="utf-8", errors="replace") as f:
        xml = f.read()
    index = []
    for url in re.findall(r"<loc>(https://www\.gsmarena\.com/[a-z0-9_\-]+\.php)</loc>", xml):
        if "-pictures-" in url:
            continue
        index.append((_slug_name(url), url))
    return index


def _search_models(query: str, limit: int = 6) -> list:
    """Match query against the local GSM Arena sitemap index.

    No external search engine (they throttle datacenter IPs); the
    sitemap is cached on disk and refreshed weekly.
    """
    qtokens = _norm(query)
    if not qtokens:
        return []
    scored = []
    for name, url in _load_index():
        ntokens = set(_norm(name))
        flat = name.replace(" ", "")
        hits, exact = 0, 0
        for t in qtokens:
            if t in ntokens:
                hits += 1
                exact += 1
            elif len(t) > 1 and t in flat:
                # single letters only match whole tokens, otherwise "g"
                # would match every name containing the letter g
                hits += 1
        if hits == 0:
            continue
        # all query tokens matched wins; exact token beats substring;
        # then fewest extra tokens; then newest id
        extra = len(ntokens) - hits
        m = re.search(r"-(\d+)\.php$", url)
        pid = int(m.group(1)) if m else 0
        scored.append((hits / len(qtokens), exact, -extra, pid, name, url))
    scored.sort(reverse=True)
    return [(n, u) for _, _, _, _, n, u in scored[:limit]]


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
        import re as _re

        hl = {}
        # highlight header carries battery size even when the table lacks it
        m = _re.search(r'data-spec="batsize-hl">([^<]+)', resp.text)
        if m:
            hl["batsize"] = m.group(1).strip()
        img = soup.select_one(".specs-photo-main img")
        if img and img.get("src"):
            hl["image"] = img["src"]
        specs["_hl"] = hl
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

    def batt(specs):
        rows = specs.get("Battery", [])
        for t, v in rows:
            if "mah" in v.lower():
                return v
        size = specs.get("_hl", {}).get("batsize", "")
        if size:
            size = size if "mah" in size.lower() else f"{size} mAh"
            for t, v in rows:
                if t.lower() == "type" and v:
                    return v if "mah" in v.lower() else f"{size} ({v})"
            return size
        for t, v in rows:
            if t.lower() == "type" and v:
                return v
        return ""

    def block(*vals):
        return "\n".join(v for v in vals if v)

    disp = block(g("Display", "Type"), g("Display", "Size"), g("Display", "Resolution"))
    chip = block(g("Platform", "Chipset"), g("Platform", "CPU"), g("Platform", "GPU"))
    rear = (g("Main Camera", "Quad") or g("Main Camera", "Triple") or g("Main Camera", "Dual") or g("Main Camera", "Single") or first("Main Camera"))
    front = (g("Selfie camera", "Single") or first("Selfie camera"))
    img = specs.get("_hl", {}).get("image", "")
    rows = [
        ("Foto", f"[📷 ver foto]({img})" if img else ""),
        ("Status", g("Launch", "Status")),
        ("Network", g("Network", "Technology") or first("Network")),
        ("Weight", g("Body", "Weight")),
        ("Display", disp),
        ("Chipset", chip),
        ("Memory", g("Memory", "Internal")),
        ("Rear Camera", rear),
        ("Front Camera", front),
        ("3.5mm jack", g("Sound", "3.5mm jack")),
        ("USB", g("Comms", "USB")),
        ("Sensors", g("Features", "Sensors") or first("Features")),
        ("Battery", batt(specs)),
    ]
    lines = [f"[{name}]({url})", ""]
    for label, val in rows:
        if not val:
            continue
        if "\n" in val:
            lines.append(f"**{label}:**\n{val}")
        else:
            lines.append(f"**{label}:** {val}")
        lines.append("")
    return "\n".join(lines).rstrip()


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
