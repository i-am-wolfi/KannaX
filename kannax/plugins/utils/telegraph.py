import os

from telegraph import upload_file

from kannax import Config, Message, kannax
from kannax.utils import progress

_T_LIMIT = 5242880


@kannax.on_cmd(
    "telegraph",
    about={
        "header": "Upload file to Telegra.ph's servers",
        "types": [".jpg", ".jpeg", ".png", ".gif", ".mp4"],
        "usage": "reply {tr}telegraph to supported media : limit 5MB",
    },
)
async def telegraph_(message: Message):
    replied = message.reply_to_message
    if not replied:
        await message.err("reply to supported media")
        return
    link = await upload_media_(message)
    if not link:
        return
    await message.edit(
        f"**[Aqui, seu link Telegra.ph!](https://telegra.ph{link})**",
        disable_web_page_preview=True,
    )


async def upload_media_(message: Message):
    replied = message.reply_to_message
    if not replied:
        await message.err("responda a uma foto/gif/video.")
        return None
    photo = getattr(replied, "photo", None)
    animation = getattr(replied, "animation", None)
    video = getattr(replied, "video", None)
    document = getattr(replied, "document", None)
    doc_name = str(getattr(document, "file_name", "") or "")
    vid_name = str(getattr(video, "file_name", "") or "")
    if not (
        (photo and (photo.file_size or 0) <= _T_LIMIT)
        or (animation and (animation.file_size or 0) <= _T_LIMIT)
        or (
            video
            and vid_name.endswith((".mp4", ".mkv"))
            and (video.file_size or 0) <= _T_LIMIT
        )
        or (
            document
            and doc_name.endswith(
                (".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mkv")
            )
            and (document.file_size or 0) <= _T_LIMIT
        )
        or (getattr(replied, "sticker", None) is not None)
    ):
        await message.err("midia nao suportada! responda a foto/gif/video de ate 5MB.")
        return None
    await message.edit("`processando...`")
    try:
        dl_loc = await message.client.download_media(
            message=message.reply_to_message,
            file_name=Config.DOWN_PATH,
            progress=progress,
            progress_args=(message, "tentando fazer download"),
        )
    except Exception as dl_e:
        await message.err(f"falha no download: `{dl_e}`")
        return None
    if not dl_loc:
        await message.err("falha no download: arquivo vazio.")
        return None
    await message.edit("`fazendo upload no telegraph...`")
    try:
        response = upload_file(dl_loc)
    except Exception as t_e:
        await message.err(f"falha no upload p/ telegraph: `{t_e}`")
        return None
    finally:
        try:
            os.remove(dl_loc)
        except OSError:
            pass
    if not response:
        await message.err("telegraph retornou resposta vazia.")
        return None
    return str(response[0])
