# axionos builds by device codename (gms/vanilla)

"""última AxionOS por codinome. Ex: ,axion alioth [,axion alioth gms]"""

import datetime

import requests

from kannax import Message, kannax

_UA = {"User-Agent": "KannaX-bot"}
OTA = "https://raw.githubusercontent.com/AxionAOSP/official_devices/main/OTA/{}/{}.json"


def _human_size(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{num} {unit}"
        num /= 1024
    return f"{num:.1f} GB"


def _latest(code: str, variant: str) -> dict | None:
    resp = requests.get(OTA.format(variant.upper(), code.strip().lower()), headers=_UA, timeout=60)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    builds = resp.json().get("response", [])
    if not builds:
        return None
    return max(builds, key=lambda b: b.get("datetime", 0))


@kannax.on_cmd(
    "axion",
    about={
        "header": "AxionOS por codinome",
        "description": "Última build da AxionOS (vanilla ou gms) para o aparelho.",
        "usage": "{tr}axion [codinome] [gms|vanilla]  (ex: {tr}axion alioth)",
    },
)
async def axion_(message: Message):
    """axionos latest build"""
    if not message.input_str:
        await message.err("Forneça o codinome. Ex: `,axion alioth`", del_in=5)
        return
    parts = message.input_str.strip().split()
    code = parts[0].lower()
    variant = parts[1].upper() if len(parts) > 1 and parts[1].lower() in ("gms", "vanilla") else "VANILLA"
    await message.edit(f"`Buscando AxionOS {variant} para {code}...`")
    try:
        b = _latest(code, variant)
    except Exception as e:
        await message.edit(f"`Falha buscando AxionOS: {e}`", del_in=10)
        return
    if not b:
        other = "GMS" if variant == "VANILLA" else "VANILLA"
        try:
            alt = _latest(code, other)
        except Exception:
            alt = None
        hint = f" (tem {other})" if alt else ""
        await message.edit(f"`{code} sem build {variant}{hint}.`", del_in=10)
        return
    date = datetime.datetime.fromtimestamp(b.get("datetime", 0)).strftime("%Y-%m-%d")
    await message.edit(
        f"📱 **AxionOS {b.get('version', '?')} {variant} — {code}**\n"
        f"🦊 <code>{b.get('filename', '?')}</code>\n"
        f"📅 {date} | 🔰 **{_human_size(b.get('size', 0))}**\n\n"
        f"⬇️ [DOWNLOAD]({b.get('url', '')})",
        disable_web_page_preview=True,
    )
