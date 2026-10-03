# lineageos builds by device codename

"""baixa info/builds do LineageOS pelo codinome do aparelho"""

import datetime

import requests

from kannax import Message, kannax

LOS_API = "https://download.lineageos.org/api/v2"


def _human_size(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{num} {unit}"
        num /= 1024
    return f"{num:.1f} GB"


def _device(codename: str) -> dict | None:
    resp = requests.get(f"{LOS_API}/devices/{codename.strip().lower()}", timeout=60)
    if resp.status_code == 400:
        return None
    resp.raise_for_status()
    return resp.json()


def _latest_build(codename: str) -> dict | None:
    resp = requests.get(f"{LOS_API}/devices/{codename}/builds", timeout=60)
    resp.raise_for_status()
    builds = resp.json()
    zips = []
    for b in builds:
        for f in b.get("files", []):
            if f.get("filename", "").endswith(".zip"):
                zips.append((b.get("datetime", 0), f))
    if not zips:
        return None
    zips.sort(reverse=True)
    return zips[0][1]


@kannax.on_cmd(
    "los",
    about={
        "header": "LineageOS por codinome",
        "description": "Mostra última nightly do LineageOS para o aparelho.",
        "usage": "{tr}los [codinome]  (ex: {tr}los alioth)",
    },
)
async def los_(message: Message):
    """lineageos latest build"""
    if not message.input_str:
        await message.err("Forneça o codinome. Ex: `,los alioth`", del_in=5)
        return
    codename = message.input_str.strip().split()[0].lower()
    await message.edit(f"`Buscando LineageOS para {codename}...`")
    try:
        dev = _device(codename)
    except Exception as e:
        await message.edit(f"`Erro na API do LineageOS: {e}`", del_in=10)
        return
    if not dev:
        await message.edit(
            f"`{codename} sem suporte no LineageOS oficial. "
            "Confira o codinome em wiki.lineageos.org/devices`",
            del_in=10,
        )
        return
    try:
        build = _latest_build(codename)
    except Exception as e:
        await message.edit(f"`Erro buscando builds: {e}`", del_in=10)
        return
    if not build:
        await message.edit(f"`Sem builds para {codename}.`", del_in=10)
        return
    date = datetime.datetime.fromtimestamp(build.get("datetime", 0)).strftime("%Y-%m-%d")
    versions = ", ".join(dev.get("versions", []))
    msg = (
        f"📱 **Aparelho**: {dev.get('name', codename)}\n"
        f"🏭 **OEM**: {dev.get('oem', '?')}\n"
        f"📦 **Versões**: {versions}\n\n"
        f"🦊 <code>{build.get('filename', '?')}</code>\n"
        f"📅 {date}\n"
        f"🔰 **Size:** {_human_size(build.get('size', 0))}\n"
        f"🔑 **SHA256:** <code>{build.get('sha256', '?')[:16]}...</code>\n"
        f"🩹 **Patch:** {build.get('os_patch_level', '?')}\n\n"
        f"⬇️ <a href={build.get('url', '')}>DOWNLOAD</a> | "
        f"📖 <a href={dev.get('info_url', '')}>WIKI</a>"
    )
    await message.edit(msg, disable_web_page_preview=True)
