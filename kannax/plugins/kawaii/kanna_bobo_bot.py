# device specs via GSM Arena (no bot needed)

"""puxa ficha de celular direto do gsmarena.com"""

import asyncio
import base64
import hashlib
import json
import os
import re
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

from kannax import Message, kannax

_UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}
_SITEMAP_URL = "https://www.gsmarena.com/sitemaps/phones.xml"
_SITEMAP_TTL = 7 * 24 * 3600  # refresh weekly
_SEARCH_TTL = 7 * 24 * 3600  # cache de busca online (acerto)
_SEARCH_MISS_TTL = 3600  # cache de busca sem resultado (curto: pode ter sido rate limit)
_CAPTION_LIMIT = 1000  # limite real do Telegram é 1024 (folga p/ markdown)
_PHONE_URL_RE = re.compile(r"^https://www\.gsmarena\.com/[a-z0-9_]+-\d+\.php$")

# ordem de importância das linhas do card (as últimas caem primeiro
# quando a ficha precisa caber na legenda da foto)
_CARD_ORDER = [
    "Status",
    "Display",
    "Chipset",
    "Memory",
    "Rear Camera",
    "Front Camera",
    "Battery",
    "Sensors",
    "WiFi",
    "Weight",
    "USB",
    "Bluetooth",
    "3.5mm jack",
    "Network",
]


def _norm(text: str) -> list:
    return [t for t in re.sub(r"[^a-z0-9]+", " ", text.lower()).split() if t]


def _slug_name(url: str) -> str:
    slug = url.rsplit("/", 1)[1][:-4]
    slug = re.sub(r"-\d+$", "", slug)
    return slug.replace("_", " ")


def _cache_dir() -> str:
    from kannax import Config

    cache_dir = os.path.join(getattr(Config, "DOWN_PATH", "downloads/"), ".gsm_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _sitemap_path() -> str:
    return os.path.join(_cache_dir(), "phones.xml")


def _load_index() -> list:
    """(name, url) for every GSM Arena phone, cached from phones.xml.

    Atenção: o sitemap do GSM Arena é atualizado só de vez em quando
    (última vez em jun/2025), então aparelhos novos não aparecem aqui.
    Quando a busca local não dá match exato usamos a busca online.
    """
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


def _variants(query: str) -> list:
    """Query fallbacks for model numbers.

    j500m -> j500 -> j5 (sufixo de variante preso a um dígito, depois raiz
    do modelo). Palavras soltas NÃO são cortadas: antes "s25 fe" virava
    "s25" e devolvia o S25 comum no lugar do S25 FE.
    """
    out = [query.strip()]
    q = query.strip().lower()
    toks = q.split()
    if not toks:
        return out
    last = toks[-1]
    # só corta letras coladas a um dígito: "j500m" -> "j500" (nunca "fe")
    if re.search(r"\d[a-z]+$", last):
        base = re.sub(r"[a-z]+$", "", last)
        v2 = " ".join(toks[:-1] + [base])
        if v2 and v2 not in out:
            out.append(v2)
        # raiz do modelo (só faz sentido quando é um token só): j500 -> j5
        if len(toks) == 1:
            m = re.match(r"^([a-z]+)\d*?(\d)", base)
            if m:
                v3 = f"{m.group(1)}{m.group(2)}"
                if v3 not in out:
                    out.append(v3)
    return out


def _local_match(query: str, index: list, limit: int) -> list:
    """Match query against the local GSM Arena sitemap index.

    Retorna (results, confident): results no formato (name, url).
    confident=True só quando a query EXATA bateu por completo — os
    fallbacks (j500m -> j5) são só último recurso, para não devolver o
    aparelho errado quando existe um mais novo fora do sitemap.
    """
    best = []
    for i, variant in enumerate(_variants(query)):
        vtokens = _norm(variant)
        if not vtokens:
            continue
        scored = []
        for name, url in index:
            ntokens = set(_norm(name))
            flat = name.replace(" ", "")
            hits, exact = 0, 0
            for t in vtokens:
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
            scored.append((hits / len(vtokens), exact, -extra, pid, name, url))
        scored.sort(reverse=True)
        if scored and scored[0][0] == 1.0 and i == 0:
            return [(n, u) for _, _, _, _, n, u in scored[:limit]], True
        if scored and (not best or scored[0] > best[0]):
            best = scored
    return [(n, u) for _, _, _, _, n, u in best[:limit]], False


def _extract_phone_urls(html: str, limit: int) -> list:
    """Extrai URLs de páginas de aparelho do GSM Arena de uma SERP."""
    out = []

    def add(u: str) -> None:
        u = u.split("#")[0].replace("&amp;", "&")
        if u.startswith("/"):
            u = "https://www.gsmarena.com" + u
        elif not u.startswith("http"):
            u = "https://www.gsmarena.com/" + u
        if _PHONE_URL_RE.match(u) and u not in out:
            out.append(u)

    for raw in re.findall(r'href="([^"]+)"', html):
        add(raw)
        # DDG esconde o destino em uddg=<url-encoded>
        if "uddg=" in raw:
            m = re.search(r"uddg=([^&\"]+)", raw)
            if m:
                add(urllib.parse.unquote(m.group(1)))
    # Bing esconde o destino em u=a1<base64>
    for m in re.finditer(r"u=a1([A-Za-z0-9_\-]+)", html):
        s = m.group(1) + "=" * (-len(m.group(1)) % 4)
        try:
            add(base64.urlsafe_b64decode(s).decode("utf-8", "replace"))
        except Exception:
            pass
    return out[:limit]


def _gsmarena_search(query: str, limit: int) -> list:
    """Busca no próprio GSM Arena (results.php3). Pode cair em rate
    limit/Turnstile — nesse caso devolve vazio e outro motor assume."""
    for host in ("https://www.gsmarena.com", "https://m.gsmarena.com"):
        try:
            resp = requests.get(
                host + "/results.php3",
                params={"sQuickSearch": "yes", "sName": query},
                headers=_UA,
                timeout=40,
            )
        except Exception:
            continue
        if resp.status_code != 200:
            continue
        head = resp.text[:4000].lower()
        if "turnstile" in head or "challenge" in head or "too many requests" in head:
            continue
        urls = _extract_phone_urls(resp.text, limit)
        if urls:
            return urls
    return []


def _brave_search(query: str, limit: int) -> list:
    q = urllib.parse.quote(f"gsmarena {query}")
    resp = requests.get(f"https://search.brave.com/search?q={q}", headers=_UA, timeout=40)
    resp.raise_for_status()
    return _extract_phone_urls(resp.text, limit)


def _bing_search(query: str, limit: int) -> list:
    q = urllib.parse.quote(f"site:gsmarena.com {query}")
    resp = requests.get(f"https://www.bing.com/search?q={q}", headers=_UA, timeout=40)
    resp.raise_for_status()
    return _extract_phone_urls(resp.text, limit)


def _ddg_search(query: str, limit: int) -> list:
    q = urllib.parse.quote(f"gsmarena {query}")
    resp = requests.get(f"https://html.duckduckgo.com/html/?q={q}", headers=_UA, timeout=40)
    resp.raise_for_status()
    return _extract_phone_urls(resp.text, limit)


def _web_search(query: str, limit: int = 6) -> list:
    """Busca online (cacheada) quando o sitemap local está defasado."""
    key = hashlib.sha1(" ".join(_norm(query)).encode()).hexdigest()[:16]
    path = os.path.join(_cache_dir(), f"search_{key}.json")
    if os.path.isfile(path):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = None
        if data:
            ttl = _SEARCH_TTL if data.get("u") else _SEARCH_MISS_TTL
            if time.time() - data.get("t", 0) < ttl:
                return [(_slug_name(u), u) for u in data.get("u", [])][:limit]
    urls = []
    # buscadores primeiro (não pesam no GSM Arena, que também precisa
    # servir a própria ficha); a busca do site fica como último recurso
    for engine in (_brave_search, _bing_search, _ddg_search, _gsmarena_search):
        try:
            urls = engine(query, limit)
        except Exception:
            urls = []
        if urls:
            break
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"t": time.time(), "u": urls}, f)
    except Exception:
        pass
    return [(_slug_name(u), u) for u in urls][:limit]


def _search_models(query: str, limit: int = 6) -> list:
    """Localiza o aparelho no sitemap e, se necessário, na web."""
    if not _norm(query):
        return []
    index = _load_index()
    results, confident = _local_match(query, index, limit)
    if confident:
        return results
    try:
        web = _web_search(query, limit)
    except Exception:
        web = []
    if web:
        return web
    return results


def _get_spec(url: str, row: str):
    """Spec rows for a section title (or the whole card when row='all')."""
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
        hl = {}
        for k, v in re.findall(r'data-spec="([a-z0-9\-]+)"[^>]*>([^<]{0,200})', resp.text):
            v = v.strip()
            if v and k not in hl:
                hl[k] = v
        img = soup.select_one(".specs-photo-main img")
        if img and img.get("src"):
            hl["image"] = img["src"]
        specs["_hl"] = hl
        specs["_name"] = name
        return specs  # type: ignore[return-value]
    sec, ttl = row.split("|", 1)
    return picked.get((sec, ttl), "")


def _render_card(name: str, url: str, rows: list, sep: str = "\n") -> str:
    lines = [f"[{name}]({url})", ""]
    for label, val in rows:
        if not val:
            continue
        if sep != "\n":
            val = sep.join(p.strip() for p in val.split("\n") if p.strip())
        if "\n" in val:
            lines.append(f"**{label}:**\n{val}")
        else:
            lines.append(f"**{label}:** {val}")
        lines.append("")
    return "\n".join(lines).rstrip()


def _fmt_specs(name: str, url: str, specs: dict, max_len: int = 0) -> str:
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

    def block(*vals):
        return "\n".join(v for v in vals if v)

    hl = specs.get("_hl", {})
    bsize = hl.get("batsize-hl", "")
    bsize = bsize if "mah" in bsize.lower() else (f"{bsize} mAh" if bsize else "")
    btype = g("Battery", "Type")
    batt = btype if btype and "mah" in btype.lower() else (
        f"{bsize} ({btype})" if bsize and btype else (bsize or btype)
    )
    disp = block(hl.get("displaytype", ""), g("Display", "Size"), g("Display", "Resolution"))
    chip = block(g("Platform", "Chipset"), g("Platform", "CPU"), g("Platform", "GPU"))
    rows = [
        ("Status", hl.get("status", "") or g("Launch", "Status")),
        ("Network", hl.get("nettech", "") or first("Network")),
        ("WiFi", hl.get("wlan", "")),
        ("Bluetooth", hl.get("bluetooth", "") or g("Comms", "Bluetooth")),
        ("Weight", hl.get("weight", "") or g("Body", "Weight")),
        ("Display", disp),
        ("Chipset", chip),
        ("Memory", hl.get("internalmemory", "") or g("Memory", "Internal")),
        ("Rear Camera", hl.get("cam1modules", "")),
        ("Front Camera", hl.get("cam2modules", "")),
        ("3.5mm jack", g("Sound", "3.5mm jack")),
        ("USB", g("Comms", "USB")),
        ("Sensors", hl.get("sensors", "")),
        ("Battery", batt),
    ]
    text = _render_card(name, url, rows)
    if not max_len or len(text) <= max_len:
        return text
    # não coube na legenda da foto: junta as linhas e vai cortando as
    # informações menos importantes até caber
    ordered = sorted(
        [r for r in rows if r[1]],
        key=lambda r: _CARD_ORDER.index(r[0]) if r[0] in _CARD_ORDER else 99,
    )
    while len(ordered) > 1:
        compact = _render_card(name, url, ordered, sep=" · ")
        if len(compact) <= max_len:
            return compact
        ordered.pop()
    compact = _render_card(name, url, ordered, sep=" · ")
    return compact[:max_len]


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
    except Exception as e:
        await message.edit(f"`Falha lendo a ficha: {e}`", del_in=10)
        return
    if not isinstance(specs, dict) or not specs:
        # página não abriu (rate limit do GSM Arena, por ex.)
        await message.edit(
            f"`Não consegui ler a ficha agora. Tente de novo em alguns instantes.`",
            del_in=10,
        )
        return
    title = specs.get("_name") or name
    img = specs.get("_hl", {}).get("image", "")
    if img:
        # a ficha vai inteira como legenda da foto (uma mensagem só);
        # se não couber nos 1024, o excedente menos importante é cortado
        caption = _fmt_specs(title, url, specs, max_len=_CAPTION_LIMIT)
        try:
            await message.client.send_photo(
                chat_id=message.chat.id, photo=img, caption=caption
            )
            await message.delete()
            return
        except Exception:
            pass
    # sem foto (ou foto falhou): manda a ficha completa em texto
    await message.edit(
        _fmt_specs(title, url, specs), disable_web_page_preview=True
    )
