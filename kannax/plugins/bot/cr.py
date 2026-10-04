# crdroid builds by device codename

"""última crDroid por codinome. Ex: ,cr alioth [,cr alioth 10]"""

import re

import requests
from bs4 import BeautifulSoup

from kannax import Message, kannax

_UA = {"User-Agent": "Mozilla/5.0"}
BASE = "https://crdroid.net"


def _versions(code: str) -> list:
    resp = requests.get(f"{BASE}/{code}", headers=_UA, timeout=60)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return sorted({int(v) for v in re.findall(rf"{re.escape(code)}/(\d+)", resp.text)})


def _build(code: str, ver: int) -> dict:
    resp = requests.get(f"{BASE}/{code}/{ver}", headers=_UA, timeout=60)
    resp.raise_for_status()
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")
    txt = soup.get_text(" | ", strip=True)

    def field(label: str) -> str:
        m = re.search(rf"{label} \| ([^|]+)", txt)
        return m.group(1).strip() if m else "?"

    zips = re.findall(r"https://sourceforge\.net/projects/crdroid/files/[^\"']+\.zip/download", html)
    clog = re.findall(r"(?:\.\./|\.\.|https://crdroid\.net/)?(changelog/[^\"']+\.txt)", html)
    md5 = re.findall(r"value=['\"]([a-f0-9]{32})['\"]", html)
    sha = re.findall(r"value=['\"]([a-f0-9]{64})['\"]", html)
    return {
        "maintainer": field("Maintainer"),
        "version": field("Version"),
        "android": field("Android"),
        "date": field("Build date"),
        "size": field("ZIP size"),
        "zip": zips[0] if zips else "",
        "changelog": (clog[0] if clog else ""),
        "md5": md5[0] if md5 else "",
        "sha256": sha[0] if sha else "",
    }


@kannax.on_cmd(
    "cr",
    about={
        "header": "crDroid por codinome",
        "description": "Última build da crDroid para o aparelho.",
        "usage": "{tr}cr [codinome] [versão]  (ex: {tr}cr alioth)",
    },
)
async def cr_(message: Message):
    """crdroid latest build"""
    if not message.input_str:
        await message.err("Forneça o codinome. Ex: `,cr alioth`", del_in=5)
        return
    parts = message.input_str.strip().split()
    code = parts[0].lower()
    await message.edit(f"`Buscando crDroid para {code}...`")
    try:
        vers = _versions(code)
    except Exception as e:
        await message.edit(f"`Falha buscando crDroid: {e}`", del_in=10)
        return
    if not vers:
        await message.edit(f"`{code} sem suporte na crDroid.`", del_in=10)
        return
    want = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else max(vers)
    if want not in vers:
        await message.edit(
            f"`crDroid {want} não existe para {code}. Versões: {vers}`", del_in=10
        )
        return
    try:
        b = _build(code, want)
    except Exception as e:
        await message.edit(f"`Falha lendo a build: {e}`", del_in=10)
        return
    msg = (
        f"📱 **crDroid {b['version']} — {code}**\n"
        f"👤 **Maintainer:** {b['maintainer']}\n"
        f"🤖 **Android:** {b['android']}\n"
        f"📅 **Build:** {b['date']} | 🔰 **{b['size']}**\n"
    )
    if b["md5"]:
        msg += f"🔑 **MD5:** `{b['md5']}`\n"
    msg += "\n"
    if b["zip"]:
        msg += f"⬇️ [DOWNLOAD]({b['zip']})\n"
    if b["changelog"]:
        clog = b["changelog"] if b["changelog"].startswith("http") else f"{BASE}/{b['changelog']}"
        msg += f"📝 [Changelog]({clog})\n"
    msg += f"🌐 [Outras versões]({BASE}/{code})"
    await message.edit(msg, disable_web_page_preview=True)
