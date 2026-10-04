# zygisknext zip (latest)

"""manda o link do ZygiskNext mais recente. Ex: ,zygisk"""

import re

import requests

from kannax import Message, kannax

_UA = {"User-Agent": "Mozilla/5.0"}
_TAG_RE = re.compile(r"/LSPosed/ZygiskNext/releases/tag/([^\"']+)")


def _latest():
    page = requests.get("https://github.com/LSPosed/ZygiskNext/releases", headers=_UA, timeout=60)
    page.raise_for_status()
    tags = list(dict.fromkeys(_TAG_RE.findall(page.text)))
    if not tags:
        raise RuntimeError("nenhuma release encontrada")
    tag = tags[0]
    assets = requests.get(
        f"https://github.com/LSPosed/ZygiskNext/releases/expanded_assets/{tag}",
        headers={"Accept": "text/html", **_UA},
        timeout=60,
    )
    assets.raise_for_status()
    zips = []
    for href in sorted(set(re.findall(r'href="([^"]+)"', assets.text))):
        if href.endswith(".zip"):
            zips.append(href if href.startswith("http") else f"https://github.com{href}")
    if not zips:
        raise RuntimeError(f"sem ZIP na release {tag}")
    return tag, zips


@kannax.on_cmd(
    "zygisk",
    about={
        "header": "ZygiskNext mais recente",
        "description": "Manda o link do ZIP do ZygiskNext oficial.",
        "usage": "{tr}zygisk",
    },
)
async def zygisk_(message: Message):
    """latest zygisknext zip"""
    await message.edit("`Buscando ZygiskNext...`")
    try:
        tag, zips = _latest()
    except Exception as e:
        await message.edit(f"`Falha buscando ZygiskNext: {e}`", del_in=10)
        return
    lines = [f"⚡ **ZygiskNext `{tag}`**", ""]
    for z in zips:
        lines.append(f"⬇️ [{z.rsplit('/', 1)[1]}]({z})")
    await message.edit("\n".join(lines), disable_web_page_preview=True)
