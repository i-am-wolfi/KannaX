# lsposed zips (latest, riru + zygisk)

"""manda os links do LSPosed mais recente. Ex: ,lsp"""

import re

import requests

from kannax import Message, kannax

_UA = {"User-Agent": "Mozilla/5.0"}
_TAG_RE = re.compile(r"/LSPosed/LSPosed/releases/tag/([^\"']+)")


def _latest():
    page = requests.get("https://github.com/LSPosed/LSPosed/releases", headers=_UA, timeout=60)
    page.raise_for_status()
    tags = list(dict.fromkeys(_TAG_RE.findall(page.text)))
    if not tags:
        raise RuntimeError("nenhuma release encontrada")
    tag = tags[0]
    assets = requests.get(
        f"https://github.com/LSPosed/LSPosed/releases/expanded_assets/{tag}",
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
    "lsp",
    about={
        "header": "LSPosed mais recente",
        "description": "Manda os links dos ZIPs do LSPosed oficial (riru + zygisk).",
        "usage": "{tr}lsp",
    },
)
async def lsp_(message: Message):
    """latest lsposed zips"""
    await message.edit("`Buscando LSPosed...`")
    try:
        tag, zips = _latest()
    except Exception as e:
        await message.edit(f"`Falha buscando LSPosed: {e}`", del_in=10)
        return
    lines = [f"🧩 **LSPosed `{tag}`**", ""]
    for z in zips:
        name = z.rsplit("/", 1)[1]
        flavor = "riru" if "riru" in name.lower() else ("zygisk" if "zygisk" in name.lower() else "zip")
        lines.append(f"⬇️ [{flavor}]({z})")
    await message.edit("\n".join(lines), disable_web_page_preview=True)
