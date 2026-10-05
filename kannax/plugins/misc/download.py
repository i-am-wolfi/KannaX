""" downloader """

import asyncio
import math
import os
from datetime import datetime
from typing import Tuple, Union
from urllib.parse import unquote_plus, urlparse

import requests

from kannax import Config, Message, kannax
from kannax.utils import humanbytes, progress
from kannax.utils.exceptions import ProcessCanceled

LOGGER = kannax.getLogger(__name__)

_BROWSER_UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}


@kannax.on_cmd(
    "download",
    about={
        "header": "Download files to server",
        "usage": "{tr}download [url | reply to telegram media]",
        "examples": "{tr}download https://speed.hetzner.de/100MB.bin | testing upload.bin",
    },
    check_downpath=True,
)
async def down_load_media(message: Message):
    """download from tg and url"""
    if message.reply_to_message and message.reply_to_message.media:
        resource = message.reply_to_message
    elif message.input_str:
        resource = message.input_str
    else:
        await message.edit("Please read `.help download`", del_in=5)
        return
    try:
        dl_loc, d_in = await handle_download(message, resource)
    except ProcessCanceled:
        await message.edit("`Process Canceled!`", del_in=5)
    except Exception as e_e:  # pylint: disable=broad-except
        await message.err(e_e)
    else:
        await message.edit(f"Downloaded to `{dl_loc}` in {d_in} seconds")


async def handle_download(
    message: Message, resource: Union[Message, str]
) -> Tuple[str, int]:
    """download from resource"""
    if isinstance(resource, Message):
        return await tg_download(message, resource)
    return await url_download(message, resource)


def _file_name(url: str, resp=None) -> str:
    """Resolve a sane filename: Content-Disposition > URL path.

    Strips SourceForge-style /download suffix (basename would be
    literally 'download').
    """
    if resp is not None:
        disp = resp.headers.get("Content-Disposition", "")
        if "filename=" in disp:
            name = disp.split("filename=")[1].strip().strip("\"'; ")
            if name:
                return unquote_plus(name)
    path = urlparse(url).path.rstrip("/")
    if path.endswith("/download"):
        path = path[: -len("/download")]
    name = unquote_plus(os.path.basename(path))
    return name or f"file_{int(datetime.now().timestamp())}"


async def url_download(message: Message, url: str) -> Tuple[str, int]:
    """download from link (streamed requests, progress + cancel)"""
    await message.edit("`Downloading From URL...`")
    if "sourceforge.net" in urlparse(url).netloc:
        # Cloudflare blocks every automated client from servers
        # (requests, SmartDL, curl, even real headless Chromium).
        # Fail fast with guidance instead of a cryptic 403.
        raise RuntimeError(
            "SourceForge bloqueia download automatizado deste servidor "
            "(Cloudflare). Baixe no PC/celular e envie o arquivo ao bot, "
            "ou use ,upload respondendo a ele."
        )
    start_t = datetime.now()
    custom_file_name = unquote_plus(os.path.basename(url))
    if "|" in url:
        url, c_file_name = url.split("|", maxsplit=1)
        url = url.strip()
        if c_file_name:
            custom_file_name = c_file_name.strip()
    def _get():
        return requests.get(url, headers=_BROWSER_UA, timeout=120, stream=True)

    try:
        resp = await asyncio.to_thread(_get)
        resp.raise_for_status()
    except Exception as dl_e:
        raise RuntimeError(f"falha baixando URL: {dl_e}") from dl_e
    if custom_file_name in ("download", "") and "|" not in (message.input_str or ""):
        custom_file_name = _file_name(url, resp)
    dl_loc = os.path.join(Config.DOWN_PATH, custom_file_name)
    total = int(resp.headers.get("Content-Length") or 0)
    downloaded = 0
    last_edit = 0.0
    try:
        with open(dl_loc, "wb") as f:
            for chunk in resp.iter_content(1024 * 256):
                if message.process_is_canceled:
                    raise ProcessCanceled
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                now = datetime.now().timestamp()
                if now - last_edit >= Config.EDIT_SLEEP_TIMEOUT:
                    last_edit = now
                    pct = (downloaded / total * 100) if total else 0
                    bar = "".join(
                        Config.FINISHED_PROGRESS_STR for _ in range(math.floor(pct / 5))
                    ) + "".join(
                        Config.UNFINISHED_PROGRESS_STR
                        for _ in range(20 - math.floor(pct / 5))
                    )
                    await message.try_to_edit(
                        f"__trying to download__\n```[{bar}]```\n"
                        f"**Progress** : `{round(pct, 2)}%`\n"
                        f"**URL** : `{url}`\n"
                        f"**FILENAME** : `{custom_file_name}`\n"
                        f"**Completed** : `{humanbytes(downloaded)}`\n"
                        f"**Total** : `{humanbytes(total)}`\n",
                        disable_web_page_preview=True,
                    )
    except ProcessCanceled:
        try:
            os.remove(dl_loc)
        except OSError:
            pass
        raise
    except Exception as dl_e:
        try:
            os.remove(dl_loc)
        except OSError:
            pass
        raise RuntimeError(f"falha salvando download: {dl_e}") from dl_e
    return dl_loc, (datetime.now() - start_t).seconds


async def tg_download(message: Message, to_download: Message) -> Tuple[str, int]:
    """download from tg file"""
    await message.edit("`Downloading From TG...`")
    start_t = datetime.now()
    custom_file_name = Config.DOWN_PATH
    if message.filtered_input_str:
        custom_file_name = os.path.join(
            Config.DOWN_PATH, message.filtered_input_str.strip()
        )
    dl_loc = await message.client.download_media(
        message=to_download,
        file_name=custom_file_name,
        progress=progress,
        progress_args=(message, "trying to download"),
    )
    if message.process_is_canceled:
        raise ProcessCanceled
    if not isinstance(dl_loc, str):
        raise TypeError("File Corrupted!")
    dl_loc = os.path.join(Config.DOWN_PATH, os.path.basename(dl_loc))
    return dl_loc, (datetime.now() - start_t).seconds
