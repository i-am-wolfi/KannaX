# by @fnixdev

import asyncio

from pyrogram.errors import YouBlockedUser

from kannax import Message, kannax
from kannax.utils.exceptions import StopConversation


@kannax.on_cmd(
    "d",
    about={
        "header": "Device description",
        "description": "Obtenha todos os dados de um dispositivo via @PyKoroneBot.",
        "usage": "{tr}d [dispositivo]",
    },
)
async def ln_user_(message: Message):
    """device desc via @PyKoroneBot"""
    device_ = (message.input_str or "").strip()
    if not device_:
        await message.edit("`Forneça um dispositivo. Ex: ,d Redmi Note 12`", del_in=5)
        return
    bot_ = "@PyKoroneBot"
    await message.edit(f"Consultando `{device_}` em {bot_} ...")
    try:
        async with kannax.conversation(bot_, timeout=30) as conv:
            try:
                await conv.send_message(f"/d {device_}")
            except YouBlockedUser:
                await message.err(f"Desbloqueie {bot_} primeiro...", del_in=5)
                return
            # bots often reply with several messages ("searching..." then
            # the result); collect follow-ups and keep the longest text
            # instead of blindly showing the first one.
            candidates = []
            try:
                first = await conv.get_response(mark_read=True)
                if first is not None:
                    candidates.append(first)
            except asyncio.TimeoutError:
                pass
            for _ in range(3):
                try:
                    nxt = await conv.get_response(timeout=8, mark_read=True)
                    if nxt is None:
                        break
                    candidates.append(nxt)
                except (asyncio.TimeoutError, Exception):
                    break
            if not candidates:
                await message.edit(
                    f"{bot_} não respondeu em 30s. "
                    f"Abra {bot_} e mande /start uma vez, depois tente de novo.",
                    del_in=10,
                )
                return
            def _score(m):
                mk = getattr(m, "reply_markup", None)
                if mk and getattr(mk, "inline_keyboard", None):
                    return (1, 0)  # device picker buttons win over plain text
                t = getattr(m, "text", None) or getattr(m, "caption", None) or ""
                return (0, len(t))

            response = max(candidates, key=_score)
    except StopConversation as sc_e:
        if "already started" in str(sc_e):
            await message.edit(
                "Já há uma consulta em andamento com esse bot. "
                "Aguarde concluir e tente de novo.",
                del_in=5,
            )
        else:
            await message.edit(f"Conversa encerrada: `{sc_e}`", del_in=5)
        return
    except YouBlockedUser:
        await message.err(f"Desbloqueie {bot_} primeiro...", del_in=5)
        return
    except Exception as e:
        await message.edit(f"<b>ERRO:</b> <code>{e}</code>")
        return
    text = getattr(response, "text", None) or getattr(response, "caption", None)
    markup = getattr(response, "reply_markup", None)
    if markup and getattr(markup, "inline_keyboard", None):
        # multiple devices: bot sent buttons to pick one. Forward it
        # (forward keeps buttons working; a copy would kill callbacks).
        # The user taps the phone they want right in the chat.
        try:
            await response.forward(chat_id=message.chat.id)
            await message.delete()
        except Exception as fwd_e:
            await message.edit(
                f"Encontrei opções mas não consegui encaminhar: `{fwd_e}`",
                del_in=10,
            )
        return
    if not text:
        # media/sticker reply: copy the bot message itself
        # so the result still reaches the chat
        try:
            await response.copy(chat_id=message.chat.id)
            await message.delete()
        except Exception as fwd_e:
            await message.edit(
                f"O bot respondeu com mídia sem texto e não consegui encaminhar: `{fwd_e}`",
                del_in=10,
            )
        return
    html = text.html if hasattr(text, "html") else str(text)
    await message.edit(html, parse_mode="html")
