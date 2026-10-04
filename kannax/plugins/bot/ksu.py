# kernelsu manager apk (latest, official repo)

"""manda o link do KernelSU manager mais recente. Ex: ,ksu"""

import re

import requests

from kannax import Message, kannax

_UA = {"User-Agent": "Mozilla/5.0"}
_TAG_RE = re.compile(r"/tiann/KernelSU/releases/tag/(v?[\d.]+)")


def _latest():
    page = requests.get("https://github.com/tiann/KernelSU/releases", headers=_UA, timeout=60)
    page.raise_for_status()
    tags = list(dict.fromkeys(_TAG_RE.findall(page.text)))
    if not tags:
        raise RuntimeError("nenhuma release encontrada")
    tag = tags[0]
    assets = requests.get(
        f"https://github.com/tiann/KernelSU/releases/expanded_assets/{tag}",
        headers={"Accept": "text/html", **_UA},
        timeout=60,
    )
    assets.raise_for_status()
    for href in re.findall(r'href="([^"]+)"', assets.text):
        if href.endswith(".apk"):
            return tag, href if href.startswith("http") else f"https://github.com{href}"
    raise RuntimeError(f"sem APK na release {tag}")


@kannax.on_cmd(
    "ksu",
    about={
        "header": "KernelSU manager mais recente",
        "description": "Manda o link do APK do KernelSU manager oficial.",
        "usage": "{tr}ksu",
    },
)
async def ksu_(message: Message):
    """latest kernelsu manager"""
    await message.edit("`Buscando KernelSU...`")
    try:
        tag, url = _latest()
    except Exception as e:
        await message.edit(f"`Falha buscando KernelSU: {e}`", del_in=10)
        return
    await message.edit(
        f"🔓 **KernelSU `{tag}`**\n\n⬇️ [Manager APK]({url})",
        disable_web_page_preview=True,
    )
