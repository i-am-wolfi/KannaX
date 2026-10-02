# KKK animation plugin

"""manda K e vai editando até KKK... (20)"""

import asyncio

from pyrogram.errors.exceptions import FloodWait

from kannax import Message, kannax


@kannax.on_cmd(
    "k",
    about={
        "header": "Risada K animada",
        "description": "Manda K e edita adicionando um K por vez até 20.",
        "usage": "{tr}k [letra]",
    },
)
async def k_(message: Message):
    """K KK KKK ..."""
    letter = (message.input_str or "K").strip().split()[0][:1].upper() or "K"
    text = ""
    for _ in range(0, 20, 3):
        text += letter * 3
        try:
            await message.edit(f"`{text[:20]}`")
        except FloodWait as x_e:
            await asyncio.sleep(x_e.x)
            await message.edit(f"`{text[:20]}`")
        await asyncio.sleep(1)
