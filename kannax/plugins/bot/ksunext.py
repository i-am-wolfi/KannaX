# kernelsu-next CI builds from @ksunext_ci

"""puxa o APK spoofed do KernelSU Next pelo número do build. Ex: ,ksun 33318"""

import re

from kannax import Message, kannax

CHANNEL = "ksunext_ci"
_VER_RE = re.compile(r"v?(\d+\.\d+\.\d+)")


@kannax.on_cmd(
    "ksun",
    about={
        "header": "KernelSU Next por build",
        "description": "Busca o APK no canal @ksunext_ci pelo número do build.",
        "usage": "{tr}ksun [build]  (ex: {tr}ksun 33318)",
    },
)
async def ksun_(message: Message):
    """ksunext apk by build number"""
    build = (message.input_str or "").strip().split()[0] if message.input_str else ""
    if not build or not build.isdigit():
        await message.err("Forneça o número do build. Ex: `,ksun 33318`", del_in=5)
        return
    await message.edit(f"`Procurando build {build} em @{CHANNEL}...`")
    try:
        found = None
        async for msg in kannax.search_messages(CHANNEL, query=build, limit=20):
            if msg.document and (msg.document.file_name or "").endswith(".apk"):
                found = msg
                break
        if not found:
            # retry: any media message mentioning the build
            async for msg in kannax.search_messages(CHANNEL, query=build, limit=20):
                if msg.document or msg.photo or msg.video:
                    found = msg
                    break
    except Exception as e:
        await message.edit(
            f"`Falha lendo @{CHANNEL}: {e}\nEntre no canal uma vez e tente de novo.`",
            del_in=10,
        )
        return
    if not found:
        await message.edit(f"`Build {build} não achado em @{CHANNEL}.`", del_in=10)
        return
    text = found.text or found.caption or ""
    ver = _VER_RE.search(text)
    tag = f"v{ver.group(1)}" if ver else "versão no post"
    try:
        await found.forward(message.chat.id)
        await message.delete()
    except Exception as e:
        await message.edit(f"`Build {build} ({tag}) achado mas falhou enviar: {e}`", del_in=10)
