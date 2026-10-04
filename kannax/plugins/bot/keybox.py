# keybox xml mais recente do canal @iamxiety

"""puxa a keybox.xml mais recente. Ex: ,keybox"""

from kannax import Message, kannax

CHANNEL = "iamxiety"


@kannax.on_cmd(
    "keybox",
    about={
        "header": "Keybox mais recente",
        "description": "Encaminha a keybox.xml mais recente do canal @iamxiety.",
        "usage": "{tr}keybox",
    },
)
async def keybox_(message: Message):
    """latest keybox.xml"""
    await message.edit(f"`Buscando keybox em @{CHANNEL}...`")
    try:
        found = None
        for msg in await kannax.get_history(CHANNEL, limit=50):
            doc = getattr(msg, "document", None)
            if doc and (doc.file_name or "").lower().endswith(".xml"):
                found = msg
                break
    except Exception as e:
        await message.edit(
            f"`Falha lendo @{CHANNEL}: {e}`\n"
            f"👉 Entre no canal primeiro: https://t.me/{CHANNEL} "
            "e tente de novo.",
            del_in=10,
        )
        return
    if not found:
        await message.edit(
            f"`Nenhuma keybox achada em @{CHANNEL}.`\n"
            f"👉 Se você não está no canal, entre: https://t.me/{CHANNEL} "
            "e tente de novo.",
            del_in=10,
        )
        return
    try:
        await found.forward(message.chat.id)
        await message.delete()
    except Exception as e:
        await message.edit(f"`Keybox achada mas falhou enviar: {e}`", del_in=10)
