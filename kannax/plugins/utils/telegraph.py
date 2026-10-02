import os

import requests

from kannax import Config, Message, kannax
from kannax.utils import progress

_T_LIMIT = 5242880
_TELEGRAPH_UPLOAD_URL = "https://telegra.ph/upload"
_CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"
_ZER0X_UPLOAD_URL = "https://0x0.st"

_BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}


def _url_has_content(url: str) -> bool:
    """Check the uploaded URL actually holds data (non-zero length)."""
    try:
        resp = requests.get(url, headers=_BROWSER_UA, timeout=60, stream=True)
        resp.raise_for_status()
        total = resp.headers.get("Content-Length")
        if total is not None:
            return int(total) > 0
        # no length header: peek first chunk
        for chunk in resp.iter_content(65536):
            return len(chunk) > 0
        return False
    except Exception:
        return False


def _upload_catbox(dl_loc: str) -> str:
    """Upload to catbox.moe. Returns the full file URL."""
    fname = os.path.basename(dl_loc)
    with open(dl_loc, "rb") as f:
        resp = requests.post(
            _CATBOX_UPLOAD_URL,
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (fname, f)},
            timeout=120,
        )
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"catbox: unexpected response {url!r}")
    return url


def _upload_zer0x(dl_loc: str) -> str:
    """Upload to 0x0.st. Returns the full file URL."""
    fname = os.path.basename(dl_loc)
    with open(dl_loc, "rb") as f:
        resp = requests.post(
            _ZER0X_UPLOAD_URL,
            files={"file": (fname, f)},
            timeout=120,
        )
    resp.raise_for_status()
    url = resp.text.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"0x0.st: unexpected response {url!r}")
    return url


def _telegraph_upload(dl_loc: str) -> str:
    """Upload a file and return a direct URL.

    Tries catbox.moe first, then 0x0.st, then telegra.ph.
    (telegra.ph /upload currently answers 400 "Unknown error" to
    everything, and the `telegraph` lib wrapper is broken on top of
    that — it does response[0].get('error') while the API returns a
    plain list of strings. So telegraph is last resort.)
    Returns a full URL (catbox/0x0) or a telegra.ph path.
    """
    errors = []
    for name, func in (
        ("catbox", _upload_catbox),
        ("0x0.st", _upload_zer0x),
        ("telegraph", _upload_telegraph),
    ):
        try:
            return func(dl_loc)
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise RuntimeError("all upload hosts failed (" + "; ".join(errors) + ")")


def _upload_telegraph(dl_loc: str) -> str:
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
    url = link if link.startswith("http") else f"https://telegra.ph{link}"
    await message.edit(
        f"**[Aqui, seu link!]({url})**",
        disable_web_page_preview=True,
    )


async def _say(message: Message, quiet: bool, is_err: bool, text: str):
    """Send progress/error message unless quiet (caller reports itself)."""
    if quiet:
        return
    if is_err:
        await message.err(text)
    else:
        await message.edit(text)


async def upload_media_(message: Message, quiet: bool = False):
    replied = message.reply_to_message
    if not replied:
        if not quiet:
            await _say(message, quiet, True, "responda a uma foto/gif/video.")
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
        await _say(message, quiet, True, "midia nao suportada! responda a foto/gif/video de ate 5MB.")
        return None
    await _say(message, quiet, False, "`processando...`")
    try:
        dl_loc = await message.client.download_media(
            message=message.reply_to_message,
            file_name=Config.DOWN_PATH,
            progress=progress,
            progress_args=(message, "tentando fazer download"),
        )
    except Exception as dl_e:
        await _say(message, quiet, True, f"falha no download: `{dl_e}`")
        return None
    if not dl_loc:
        await _say(message, quiet, True, "falha no download: arquivo vazio.")
        return None
    try:
        if os.path.getsize(dl_loc) == 0:
            await _say(message, quiet, True, "falha no download: arquivo veio vazio (0 bytes). Tente outra midia.")
            return None
    except OSError as size_e:
        await _say(message, quiet, True, f"falha no download: `{size_e}`")
        return None
    await _say(message, quiet, False, "`fazendo upload...`")
    try:
        response = _telegraph_upload(dl_loc)
    except Exception as t_e:
        await _say(message, quiet, True, f"falha no upload: `{t_e}`")
        return None
    finally:
        try:
            os.remove(dl_loc)
        except OSError:
            pass
    if not response:
        await _say(message, quiet, True, "upload retornou resposta vazia.")
        return None
    url = response if response.startswith("http") else f"https://telegra.ph{response}"
    if not _url_has_content(url):
        await _say(message, quiet, True, 
            "o host retornou um arquivo vazio (0 bytes). "
            "Tente outra midia ou outro formato."
        )
        return None
    return response
