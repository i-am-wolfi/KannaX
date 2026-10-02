# new alive plugin for KannaX by @fnixdev

"""novo alive para kannax"""

import os
import tempfile

import requests

from kannax import Config, Message, get_collection, kannax, get_version
from kannax.utils import rand_array
from kannax.plugins.bot.ialive import Bot_Alive 
from kannax.versions import __python_version__
from kannax.plugins.utils.telegraph import upload_media_


SAVED = get_collection("ALIVE_DB")

ALIVE_MSG = {}

async def _init():
    global ALIVE_MEDIA, ALIVE_MSG  # pylint: disable=global-statement
    link = await SAVED.find_one({"_id": "ALIVE_MEDIA"})
    if link:
        ALIVE_MEDIA = link["link"]
    _AliveMsg = await SAVED.find_one({"_id": "CUSTOM_MSG"})
    if _AliveMsg:
        ALIVE_MSG = _AliveMsg["data"]


@kannax.on_cmd(
    "setamedia",
    about={
        "header": "Set alive media",
        "description": "Voçê pode definir uma mídia para aparecer em seu Alive",
        "flags": {
            "-r": "reset alive media.",
        },
    },
)
@kannax.on_cmd(
    "setalive",
    about={
        "header": "Set alive media (alias)",
        "description": "Alias de setamedia: responda a uma foto/gif/video para definir a Alive Media",
        "flags": {
            "-r": "reset alive media.",
        },
    },
)
async def ani_save_media_alive(message: Message):
    """set media alive"""
    found = await SAVED.find_one({"_id": "ALIVE_MEDIA"})
    if "-r" in message.flags:
        if not found:
            return await message.edit("`Nenhuma Media foi definida ainda.`", del_in=5)
        await SAVED.delete_one({"_id": "ALIVE_MEDIA"})
        return await message.edit("`Alive Media restaurada para o padrão.`", del_in=5)
    replied = message.reply_to_message
    if not replied:
        return await message.err("`Responda a uma foto/gif/video para definir uma Alive Media.`")
    link_ = await upload_media_(message)
    if not link_:
        return await message.edit(
            "`setalive falhou: veja o erro acima. Responda a uma foto/gif/video de ate 5MB.`",
            del_in=10,
        )
    media = link_ if link_.startswith("http") else f"https://telegra.ph{link_}"
    await SAVED.update_one(
            {"_id": "ALIVE_MEDIA"}, {"$set": {"link": media}}, upsert=True
        )
    await message.edit("`Alive Media definida com sucesso!`", del_in=5, log=True)


@kannax.on_cmd(
    "setamsg",
    about={
        "header": "Define uma mensagem para alive",
        "description": "Voçê pode definir uma mensagem para aparecer em seu Alive",
    },
)
async def save_msg_alive(message: Message):
    """set alive msg"""
    rep = message.input_or_reply_raw
    if not rep:
        return await message.edit("`Você precisa digitar ou responder a uma mensagem pra salva-la`", del_in=6)
    if len(rep) > 500:
        return await message.edit("`Essa mensagem é muito longa, o limite é de 500 caracteres.`", del_in=5)
    try:
        await SAVED.update_one(
            {"_id": "ALIVE_MSG"}, {"$set": {"data": rep}}, upsert=True
        )
        await message.edit("`Mensagem para alive definida com sucesso!`", del_in=5, log=True)
    except Exception as e:
        await message.err(f"Invalid Syntax\n\n`{e}`")


@kannax.on_cmd(
    "alive",
    about={
        "header": "Alive apenas",
    },
)
async def view_del_ani(message: Message):
    """new alive"""
    _findpma = await SAVED.find_one({"_id": "ALIVE_MEDIA"})
    _findamsg = await SAVED.find_one({"_id": "ALIVE_MSG"})
    media = (_findpma.get("link") if _findpma else None) or Config.ALIVE_MEDIA
    if _findamsg is None:
        mmsg = rand_array(FRASES)
    else:
        mmsg = _findamsg.get("data")
    msg = "ᴏɪ ᴍᴇsᴛʀᴇ, ᴋᴀɴɴᴀx ɪ'ᴛs ᴀʟɪᴠᴇ"
    alive_msg = f"""
{msg}

{mmsg}

• **Modo** :  `{Bot_Alive._get_mode()}`
• **Uptime**  :  `{kannax.uptime}`
• **Bot Version**  :  `v{get_version()}`
• **Python Version**  :  `v{__python_version__}`

    ✨ [sᴜᴘᴏʀᴛᴇ ](https://t.me/fnixsup) | 👾 [ʀᴇᴘᴏ](https://github.com/fnixdev/Kanna-X)
"""
    await _send_alive_media(message, media, alive_msg)
    await message.delete()


async def _send_alive_media(message: Message, media: str, caption: str) -> None:
    """Send alive media; falls back gracefully.

    1. Try the saved media (download URL locally first so Telegram
       never has to fetch it — avoids WEBPAGE_CURL_FAILED on hosts
       like files.catbox.moe or dead telegra.ph links).
    2. On any failure, retry with the Config.ALIVE_MEDIA default.
    """
    candidates = [media]
    if media != Config.ALIVE_MEDIA:
        candidates.append(Config.ALIVE_MEDIA)
    last_err = None
    for cand in candidates:
        try:
            await _send_one_alive_media(message, cand, caption)
            return
        except Exception as e:
            last_err = e
    await message.err(f"alive falhou: `{last_err}`")


async def _send_one_alive_media(message: Message, media: str, caption: str) -> None:
    is_anim = media.lower().split("?")[0].endswith((".gif", ".mp4"))
    local = None
    if media.startswith("http"):
        # download first: Telegram servers often refuse to fetch
        # third-party hosts (WEBPAGE_CURL_FAILED)
        local = await _download_temp(media)
    target = local or media
    try:
        if is_anim:
            await message.client.send_animation(
                chat_id=message.chat.id,
                animation=target,
                caption=caption,
            )
        else:
            await message.client.send_photo(
                chat_id=message.chat.id, photo=target, caption=caption
            )
    finally:
        if local:
            try:
                os.remove(local)
            except OSError:
                pass


async def _download_temp(url: str) -> str | None:
    """Download a URL to a temp file. Returns path or None."""
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        suffix = os.path.splitext(url.split("?")[0])[1][:8] or ".jpg"
        fd, path = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(resp.content)
        return path
    except Exception:
        return None


@kannax.on_cmd(
    "delamsg",
    about={
        "header": "Delete alive message",
        "description": "Retorna a mensagem de Alive「 para o padrão",
      },
)
async def del_a_msg(message: Message):
    """del msg alive"""
    _findamsg = await SAVED.find_one({"_id": "ALIVE_MSG"})
    if _findamsg is None:
        await message.edit("`Você ainda não definiu uma mensagem para Alive`", del_in=5)
    else:
        await SAVED.find_one_and_delete({"_id": "ALIVE_MSG"})
        await message.edit("`Alive msg excluida`", del_in=5, log=True)
 

FRASES = (
    "ʟᴇᴍʙʀᴇ-sᴇ ᴅᴀ ʟɪᴄ̧ᴀ̃ᴏ ᴇ ɴᴀ̃ᴏ ᴅᴀ ᴅᴇᴄᴇᴘᴄ̧ᴀ̃ᴏ.",
    "ᴠᴏᴄᴇ̂ ɴᴀ̃ᴏ ᴄᴏɴʜᴇᴄᴇ ᴀs ᴘᴇssᴏᴀs, ᴠᴏᴄᴇ̂ ᴄᴏɴʜᴇᴄᴇ ᴀᴘᴇɴᴀs ᴏ ǫᴜᴇ ᴇʟᴀs ᴘᴇʀᴍɪᴛᴇᴍ ǫᴜᴇ ᴠᴏᴄᴇ̂ ᴠᴇᴊᴀ.",
    "ᴀs ᴠᴇᴢᴇs ᴀs ǫᴜᴇsᴛᴏ̃ᴇs sᴀ̃ᴏ ᴄᴏᴍᴘʟɪᴄᴀᴅᴀs ᴇ ᴀs ʀᴇsᴘᴏsᴛᴀs sᴀ̃ᴏ sɪᴍᴘʟᴇs.",
    "ᴀᴍᴀʀ ᴀʟɢᴜᴇ́ᴍ ᴘʀᴏꜰᴜɴᴅᴀᴍᴇɴᴛᴇ ʟʜᴇ ᴅᴀ́ ꜰᴏʀᴄ̧ᴀ; sᴇʀ ᴀᴍᴀᴅᴏ ᴘʀᴏꜰᴜɴᴅᴀᴍᴇɴᴛᴇ ʟʜᴇ ᴅᴀ́ ᴄᴏʀᴀɢᴇᴍ.",
    "ᴠᴏᴄᴇ̂ ɴᴀ̃ᴏ ᴇ́ ᴅᴇʀʀᴏᴛᴀᴅᴏ ǫᴜᴀɴᴅᴏ ᴘᴇʀᴅᴇ, ᴍᴀs sɪᴍ ǫᴜᴀɴᴅᴏ ᴠᴏᴄᴇ̂ ᴅᴇsɪsᴛᴇ.",
    "ʜᴀ ᴍᴏᴍᴇɴᴛᴏs ǫᴜᴇ ᴠᴏᴄᴇ̂ ᴘʀᴇᴄɪsᴀ ᴅᴇsɪsᴛɪʀ ᴅᴇ ᴀʟɢᴜᴍᴀ ᴄᴏɪsᴀ ᴘᴀʀᴀ ᴘʀᴇsᴇʀᴠᴀʀ ᴀ ᴏᴜᴛʀᴀ.",
    "ᴀ ᴠɪᴅᴀ ᴅᴀs ᴘᴇssᴏᴀs ɴᴀ̃ᴏ ᴀᴄᴀʙᴀ ǫᴜᴀɴᴅᴏ ᴇʟᴀs ᴍᴏʀʀᴇᴍ, ᴍᴀs sɪᴍ ǫᴜᴀɴᴅᴏ ᴘᴇʀᴅᴇᴍ ᴀ ꜰᴇ́.",
    "sᴇ ᴠᴏᴄᴇ̂ ᴇsᴛᴀ́ ᴠɪᴠᴏ ᴘᴏᴅᴇ ʀᴇᴄᴏᴍᴇᴄ̧ᴀʀ. ɴɪɴɢᴜᴇ́ᴍ ᴛᴇᴍ ᴏ ᴅɪʀᴇɪᴛᴏ ᴅᴇ ᴛᴇ ᴛɪʀᴀʀ ɪssᴏ.",
    "ᴏ ᴘᴇssɪᴍɪsᴍᴏ, ᴅᴇᴘᴏɪs ᴅᴇ ᴠᴏᴄᴇ̂ sᴇ ᴀᴄᴏsᴛᴜᴍᴀʀ ᴀ ᴇʟᴇ, ᴇ́ ᴛᴀ̃ᴏ ᴀɢʀᴀᴅᴀ́ᴠᴇʟ ǫᴜᴀɴᴛᴏ ᴏ ᴏᴛɪᴍɪsᴍᴏ.",
    "ᴘᴇʀᴅᴏᴀʀ ᴇ́ ʟɪʙᴇʀᴛᴀʀ ᴏ ᴘʀɪsɪᴏɴᴇɪʀᴏ... ᴇ ᴅᴇsᴄᴏʙʀɪʀ ǫᴜᴇ ᴏ ᴘʀɪsɪᴏɴᴇɪʀᴏ ᴇʀᴀ ᴠᴏᴄᴇ̂.",
    "ᴛᴜᴅᴏ ᴏ ǫᴜᴇ ᴜᴍ sᴏɴʜᴏ ᴘʀᴇᴄɪsᴀ ᴇ́ ᴀʟɢᴜᴇ́ᴍ ǫᴜᴇ ᴀᴄʀᴇᴅɪᴛᴇ ǫᴜᴇ ᴇʟᴇ ᴘᴏssᴀ sᴇʀ ʀᴇᴀʟɪᴢᴀᴅᴏ.",
    "ɴᴀ̃ᴏ ᴇsᴘᴇʀᴇ ᴘᴏʀ ᴜᴍᴀ ᴄʀɪsᴇ ᴘᴀʀᴀ ᴅᴇsᴄᴏʙʀɪʀ ᴏ ǫᴜᴇ ᴇ́ ɪᴍᴘᴏʀᴛᴀɴᴛᴇ ᴇᴍ sᴜᴀ ᴠɪᴅᴀ.",
    "ᴏ ᴘᴇssɪᴍɪsᴍᴏ, ᴅᴇᴘᴏɪs ᴅᴇ ᴠᴏᴄᴇ̂ sᴇ ᴀᴄᴏsᴛᴜᴍᴀʀ ᴀ ᴇʟᴇ, ᴇ́ ᴛᴀ̃ᴏ ᴀɢʀᴀᴅᴀ́ᴠᴇʟ ǫᴜᴀɴᴛᴏ ᴏ ᴏᴛɪᴍɪsᴍᴏ.",
    "ᴅᴇsᴄᴏʙʀɪʀ ᴄᴏɴsɪsᴛᴇ ᴇᴍ ᴏʟʜᴀʀ ᴘᴀʀᴀ ᴏ ǫᴜᴇ ᴛᴏᴅᴏ ᴍᴜɴᴅᴏ ᴇsᴛᴀ́ ᴠᴇɴᴅᴏ ᴇ ᴘᴇɴsᴀʀ ᴜᴍᴀ ᴄᴏɪsᴀ ᴅɪꜰᴇʀᴇɴᴛᴇ.",
    "ɴᴏ ꜰᴜɴᴅᴏ ᴅᴇ ᴜᴍ ʙᴜʀᴀᴄᴏ ᴏᴜ ᴅᴇ ᴜᴍ ᴘᴏᴄ̧ᴏ, ᴀᴄᴏɴᴛᴇᴄᴇ ᴅᴇsᴄᴏʙʀɪʀ-sᴇ ᴀs ᴇsᴛʀᴇʟᴀs.",
)