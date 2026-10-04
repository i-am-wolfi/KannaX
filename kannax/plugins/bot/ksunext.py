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
    # posts carry hashtags like #ci_3215 for build 33215 (last 4 digits);
    # plain-number search mismatches (33215 returned 33219), so target
    # the hashtag first, then verify the full number in the post.
    tag = f"#ci_{build[-4:]}"
    try:
        cands = []
        async for msg in kannax.search_messages(CHANNEL, query=tag, limit=20):
            cands.append(msg)
        if not cands:
            async for msg in kannax.search_messages(CHANNEL, query=build, limit=20):
                cands.append(msg)

        def _info(msg):
            text = (msg.text or msg.caption or "")
            doc = getattr(msg, "document", None)
            return (
                tag.lower() in text.lower(),
                build in text,
                bool(doc and (doc.file_name or "").endswith(".apk")),
                bool(doc or msg.photo or msg.video),
            )

        cands.sort(
            key=lambda m: (_info(m)[0], _info(m)[1], _info(m)[2]),
            reverse=True,
        )
        found = None
        for m in cands:
            has_tag, has_build, is_apk, _ = _info(m)
            if (has_tag and has_build) or (has_tag and is_apk):
                found = m
                break
        if not found:
            # last resort: any media in candidates
            found = next(
                (m for m in cands if _info(m)[3]),
                None,
            )
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
            f"`Build {build} não achado em @{CHANNEL}.`\n"
            f"👉 Se você não está no canal, entre: https://t.me/{CHANNEL} "
            "e tente de novo.",
            del_in=10,
        )
        return
    text = found.text or found.caption or ""
    ver = _VER_RE.search(text)
    tag = f"v{ver.group(1)}" if ver else "versão no post"
    try:
        await found.forward(message.chat.id)
        await message.delete()
    except Exception as e:
        await message.edit(f"`Build {build} ({tag}) achado mas falhou enviar: {e}`", del_in=10)
