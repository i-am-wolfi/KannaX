# KannaX Plugin for removing background from Images
# Author: Sumanjay (https://github.com/cyberboysumanjay) (@cyberboysumanjay)
# All rights reserved.

import os
from datetime import datetime

import requests

from kannax import Config, Message, kannax
from kannax.utils import progress

IMG_PATH = Config.DOWN_PATH + "dl_image.jpg"


@kannax.on_cmd(
    "removebg",
    about={
        "header": "Removes Background from Image (50 Calls per Month in the free API)",
        "usage": "{tr}removebg [reply to any photo | direct link of photo]",
    },
)
async def remove_background(message: Message):
    if not Config.REMOVE_BG_API_KEY:
        await message.edit(
            "Get the API from <a href='https://www.remove.bg/b/background-removal-api'>HERE "
            "</a> & add it to Heroku Config Vars <code>REMOVE_BG_API_KEY</code>",
            disable_web_page_preview=True,
            parse_mode="html",
        )
        return
    await message.edit("Analysing...")
    replied = message.reply_to_message
    if (
        replied
        and replied.media
        and (
            replied.photo
            or (replied.document and "image" in replied.document.mime_type)
        )
    ):
        start_t = datetime.now()
        if os.path.exists(IMG_PATH):
            os.remove(IMG_PATH)
        await message.client.download_media(
            message=replied,
            file_name=IMG_PATH,
            progress=progress,
            progress_args=(message, "Downloading Image"),
        )
        end_t = datetime.now()
        m_s = (end_t - start_t).seconds
        await message.edit(f"Image saved in {m_s} seconds.\nRemoving Background Now...")
        # Cooking Image: remove.bg API direta (lib removebg morreu, sem release py3.14)
        try:
            with open(IMG_PATH, "rb") as img_f:
                resp = requests.post(
                    "https://api.remove.bg/v1.0/removebg",
                    headers={"X-Api-Key": Config.REMOVE_BG_API_KEY},
                    files={"image_file": img_f},
                    data={"size": "auto"},
                    timeout=120,
                )
            resp.raise_for_status()
            rbg_img_path = IMG_PATH + "_no_bg.png"
            with open(rbg_img_path, "wb") as out_f:
                out_f.write(resp.content)
            start_t = datetime.now()
            await message.client.send_document(
                chat_id=message.chat.id,
                document=rbg_img_path,
                disable_notification=True,
                progress=progress,
                progress_args=(message, "Uploading", rbg_img_path),
            )
            await message.delete()
        except Exception:
            await message.edit("Something went wrong!\nCheck your usage quota!")
            return
    else:
        await message.edit("Reply to a photo to remove background!", del_in=5)
