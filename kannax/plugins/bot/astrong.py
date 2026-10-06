# alwaysstrong zips (latest, Zygisk implementation)

"""manda os links do AlwaysStrong mais recente. Ex: ,astrong"""

import re

import requests

from kannax import Message, kannax

_UA = {"User-Agent": "Mozilla/5.0"}
_TAG_RE = re.compile(r"/evoker0/AlwaysStrong/releases/tag/([^\"']+)")


def _latest():
    page = requests.get("https://github.com/evoker0/AlwaysStrong/releases", headers=_UA, timeout=60)
    page.raise_for_status()
    tags = list(dict.fromkeys(_TAG_RE.findall(page.text)))
    if not tags:
        raise RuntimeError("nenhuma release encontrada")
    tag = tags[0]
    assets = requests.get(
        f"https://github.com/evoker0/AlwaysStrong/releases/expanded_assets/{tag}",
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
    "astrong",
    about={
        "header": "AlwaysStrong mais recente",
        "description": "Manda os links dos ZIPs do AlwaysStrong oficial.",
        "usage": "{tr}astrong",
    },
)
async def astrong_(message: Message):
    """latest alwaysstrong zips"""
    await message.edit("`Buscando AlwaysStrong...`")
    try:
        tag, zips = _latest()
    except Exception as e:
        await message.edit(f"`Falha buscando AlwaysStrong: {e}`", del_in=10)
        return
    lines = [f"💪 **AlwaysStrong `{tag}`**", ""]
    for z in zips:
        name = z.rsplit("/", 1)[1]
        lines.append(f"⬇️ [{name}]({z})")
    await message.edit("\n".join(lines), disable_web_page_preview=True)
