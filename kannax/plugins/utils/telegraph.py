import os

import requests

from kannax import Config, Message, kannax
from kannax.utils import progress

_T_LIMIT = 5242880
_TELEGRAPH_UPLOAD_URL = "https://telegra.ph/upload"


def _telegraph_upload(dl_loc: str) -> str:
    """Upload a file to telegra.ph without the broken `telegraph` lib wrapper.

    The lib's TelegraphApi.upload_file() does response[0].get('error'),
    but telegra.ph now returns a plain list of path strings
    (e.g. ["/file/abc.jpg"]), so every upload crashed with
    "'str' object has no attribute 'get'". Posting directly and
    accepting both response shapes fixes setalive/telegraph.
    """
    with open(dl_loc, "rb") as f:
        resp = requests.post(
            _TELEGRAPH_UPLOAD_URL,
            files={"file": (os.path.basename(dl_loc), f)},
            timeout=60,
        )
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, dict):
        err = data.get("error")
        if err:
            raise RuntimeError(f"telegraph: {err}")
        # some mirrors return {"src": ...} / {"path": ...} / {"url": ...}
        for key in ("src", "path", "url"):
            if data.get(key):
                path = str(data[key])
                return path if path.startswith("/") else "/" + path
        raise RuntimeError(f"telegraph: unexpected response {data!r}")
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            if first.get("error"):
                raise RuntimeError(f"telegraph: {first['error']}")
            path = str(first.get("src") or first.get("path") or "")
        else:
            path = str(first)
        if path:
            return path if path.startswith("/") else "/" + path
    raise RuntimeError(f"telegraph: unexpected response {data!r}")


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
        response = _telegraph_upload(dl_loc)
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
    return response
