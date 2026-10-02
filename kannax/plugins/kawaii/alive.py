# new alive plugin for KannaX by @fnixdev

"""novo alive para kannax"""

import hashlib
import os
import tempfile

import requests

from kannax import Config, Message, get_collection, kannax, get_version
from kannax.utils import get_file_id, rand_array
from kannax.plugins.bot.ialive import Bot_Alive 
from kannax.versions import __python_version__
from kannax.plugins.utils.telegraph import upload_media_


SAVED = get_collection("ALIVE_DB")

_DEFAULT_ALIVE_MEDIA = "https://telegra.ph/file/8bfc66ff423f8263f8ca4.png"

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
    # Telegram file_id first: ,alive sends by file_id (instant, no
    # external host). URL upload is best-effort legacy compat.
    fid = get_file_id(replied)
    if not fid:
        return await message.err("`Responda a uma foto/gif/video para definir uma Alive Media.`")
    ftype = _reply_media_type(replied)
    link_ = await upload_media_(message)
    if link_ and not link_.startswith("http"):
        link_ = f"https://telegra.ph{link_}"
    doc = {"file_id": fid, "ftype": ftype}
    if link_:
        doc["link"] = link_
    await SAVED.update_one({"_id": "ALIVE_MEDIA"}, {"$set": doc}, upsert=True)
    extra = "" if link_ else " (sem URL espelho: hosts externos falharam, mas o alive funciona via Telegram)"
    await message.edit(f"`Alive Media definida com sucesso!`{extra}", del_in=5, log=True)


def _reply_media_type(replied) -> str:
    if getattr(replied, "animation", None) or (
        getattr(replied, "video", None)
        and str(getattr(getattr(replied, "video", None), "file_name", "") or "").endswith((".mp4", ".mkv"))
    ):
        return "animation"
    if getattr(replied, "sticker", None):
        return "sticker"
    return "photo"


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
    saved = _findpma or {}
    media = saved.get("link") or getattr(Config, "ALIVE_MEDIA", None)
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
    await _send_alive_media(
        message,
        media,
        alive_msg,
        file_id=saved.get("file_id"),
        ftype=saved.get("ftype", "photo"),
    )
    await message.delete()


async def _send_alive_media(
    message: Message, media: str, caption: str, file_id: str | None = None, ftype: str = "photo"
) -> None:
    """Send alive media; falls back gracefully.

    1. Saved Telegram file_id first (instant, no external host).
    2. Then saved/Config/default URLs (telegra.ph direct;
       third-party hosts downloaded locally to avoid
       WEBPAGE_CURL_FAILED).
    """
    last_err = None
    if file_id:
        try:
            await _send_one_alive_media(message, file_id, caption, ftype=ftype)
            return
        except Exception as e:
            last_err = e
    candidates = [m for m in (media, getattr(Config, "ALIVE_MEDIA", None), _DEFAULT_ALIVE_MEDIA) if m]
    for cand in candidates:
        try:
            await _send_one_alive_media(message, cand, caption)
            return
        except Exception as e:
            last_err = e
    await message.err(f"alive falhou: `{last_err}`")


async def _send_one_alive_media(
    message: Message, media: str, caption: str, ftype: str | None = None
) -> None:
    if ftype == "sticker":
        await message.client.send_sticker(chat_id=message.chat.id, sticker=media)
        return
    is_anim = ftype == "animation" if ftype else (media or "").lower().split("?")[0].endswith((".gif", ".mp4"))
    local = None
    own_tmp = False
    if media.startswith("http") and "telegra.ph" not in media:
        # Third-party hosts (e.g. files.catbox.moe) are often refused
        # by Telegram servers (WEBPAGE_CURL_FAILED), so download first
        # (cached on disk). telegra.ph URLs go direct — fast path,
        # same as the original behavior.
        local, own_tmp = await _download_cached(media)
        target = local or media
    else:
        target = media
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
        if local and own_tmp:
            try:
                os.remove(local)
            except OSError:
                pass


def _cache_path(url: str) -> str:
    digest = hashlib.md5(url.encode()).hexdigest()
    suffix = os.path.splitext(url.split("?")[0])[1][:8] or ".jpg"
    cache_dir = os.path.join(getattr(Config, "DOWN_PATH", "downloads/"), ".alive_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, digest + suffix)


async def _download_cached(url: str) -> tuple:
    """Download a URL, reusing a disk cache. Returns (path_or_None, own_tmp)."""
    path = _cache_path(url)
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        return path, False
    tmp = await _download_temp(url)
    if tmp:
        try:
            os.replace(tmp, path)
            return path, False
        except OSError:
            return tmp, True
    return None, False


async def _download_temp(url: str) -> str | None:
    """Download a URL to a temp file. Returns path or None."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"},
            timeout=60,
        )
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