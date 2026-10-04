# xiaomi firmware/miui (rss do xiaomifirmwareupdater)

"""últimos firmwares MIUI/HyperOS por codinome. Ex: ,xfw alioth"""

import re
import xml.etree.ElementTree as ET

import requests

from kannax import Message, kannax

_UA = {"User-Agent": "Mozilla/5.0"}
RSS = "https://raw.githubusercontent.com/XiaomiFirmwareUpdater/miui-updates-tracker/master/rss/{}.xml"


def _latest(code: str, count: int = 4) -> list:
    resp = requests.get(RSS.format(code.strip().lower()), headers=_UA, timeout=60)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    items = []
    for item in ET.fromstring(resp.content).find("channel").findall("item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        desc = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        size = re.search(r"Size:\s*([0-9.]+ ?[GMK]B)", desc)
        items.append((title, link, size.group(1) if size else "?"))
        if len(items) >= count:
            break
    return items


@kannax.on_cmd(
    "xfw",
    about={
        "header": "Firmware Xiaomi por codinome",
        "description": "Últimos MIUI/HyperOS (recovery + fastboot) do codinome.",
        "usage": "{tr}xfw [codinome]  (ex: {tr}xfw alioth)",
    },
)
async def xfw_(message: Message):
    """xiaomi firmware by codename"""
    if not message.input_str:
        await message.err("Forneça o codinome. Ex: `,xfw alioth`", del_in=5)
        return
    code = message.input_str.strip().split()[0]
    await message.edit(f"`Buscando firmware de {code}...`")
    try:
        items = _latest(code)
    except Exception as e:
        await message.edit(f"`Falha buscando firmware: {e}`", del_in=10)
        return
    if not items:
        await message.edit(f"`Nada achado para {code}. Confira o codinome.`", del_in=10)
        return
    lines = [f"📱 **Firmware {code}** (mais recentes)\n"]
    for title, link, size in items:
        kind = "Fastboot" if "fastboot" in title.lower() else ("Recovery" if "recovery" in title.lower() else "Update")
        short = re.sub(r"\s+(Fastboot|Recovery) update.*$", "", title, flags=re.IGNORECASE)
        lines.append(f"• [{kind}]({link}) — {short} ({size})")
    await message.edit("\n".join(lines), disable_web_page_preview=True)
