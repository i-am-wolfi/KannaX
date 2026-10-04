# apatch apk from github releases (numeric tags, e.g. 11224)

"""puxa o APK do APatch. Ex: ,apatch (último) ou ,apatch 11224"""

import re

import requests

from kannax import Message, kannax

REPO = "bmax121/APatch"
BASE = f"https://github.com/{REPO}"
_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
_TAG_RE = re.compile(r"/bmax121/APatch/releases/tag/(\d+)")


def _latest_tag() -> str:
    resp = requests.get(f"{BASE}/releases", headers=_UA, timeout=60)
    resp.raise_for_status()
    tags = _TAG_RE.findall(resp.text)
    if not tags:
        raise RuntimeError("nenhuma release encontrada na página")
    return tags[0]


def _apk_url(tag: str) -> str:
    resp = requests.get(
        f"{BASE}/releases/expanded_assets/{tag}",
        headers={"Accept": "text/html", **_UA},
        timeout=60,
    )
    resp.raise_for_status()
    for href in re.findall(r'href="([^"]+)"', resp.text):
        if href.endswith(".apk"):
            return href if href.startswith("http") else f"https://github.com{href}"
    raise RuntimeError(f"sem APK na release {tag}")


@kannax.on_cmd(
    "apatch",
    about={
        "header": "APatch mais recente",
        "description": "Manda o link do APK mais recente do APatch.",
        "usage": "{tr}apatch",
    },
)
async def apatch_(message: Message):
    """latest apatch apk"""
    await message.edit("`Buscando APatch...`")
    try:
        tag = _latest_tag()
        url = _apk_url(tag)
    except Exception as e:
        await message.edit(f"`Falha buscando APatch: {e}`", del_in=10)
        return
    await message.edit(
        f"🩹 **APatch `{tag}`**\n\n⬇️ [Baixar APK]({url})",
        disable_web_page_preview=True,
    )
