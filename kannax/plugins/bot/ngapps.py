# nikgapps por categoria (core/pico/basic/omni/stock/full)

"""links do NikGapps por versão do Android e variante. Ex: ,ngapps 14 core"""

from kannax import Message, kannax

SF = "https://sourceforge.net/projects/nikgapps/files/Releases"
# letra AOSP -> pasta de releases (convenção oficial do NikGapps)
LETTERS = {"12": "S", "13": "T", "14": "U", "15": "V", "16": "B"}
VARIANTS = ["Core", "Pico", "Basic", "Omni", "Stock", "Full"]
# Pico (estilo OpenGapps) ~= Core no NikGapps
ALIAS = {"pico": "Core", "nano": "Core", "micro": "Basic"}


@kannax.on_cmd(
    "ngapps",
    about={
        "header": "NikGapps por categoria",
        "description": "Links do NikGapps por versão do Android e variante.",
        "usage": "{tr}ngapps [android] [variante]  (ex: {tr}ngapps 14 core)",
    },
)
async def ngapps_(message: Message):
    """nikgapps links by android version and variant"""
    args = (message.input_str or "").strip().split()
    ver = next((a for a in args if a.isdigit()), None)
    var = next((a.capitalize() for a in args if not a.isdigit()), None)
    if var:
        var = ALIAS.get(var.lower(), var.capitalize())
        if var not in VARIANTS:
            await message.edit(
                f"`Variante inválida. Use: {', '.join(VARIANTS)}`", del_in=10
            )
            return
    if not ver or ver not in LETTERS:
        variants = " | ".join(VARIANTS)
        await message.edit(
            "**NikGapps** — escolha a versão do Android e a variante:\n\n"
            f"`{', '.join(sorted(LETTERS))}`\n"
            f"Variantes: {variants} (Pico = Core)\n\n"
            f"Ex: `,ngapps 14 core`\n"
            f"📂 [Todas as releases]({SF})",
            disable_web_page_preview=True,
        )
        return
    letter = LETTERS[ver]
    folder = f"{SF}/NikGapps-{letter}/"
    if not var:
        lines = [f"📦 **NikGapps Android {ver}** — escolha a variante:\n"]
        for v in VARIANTS:
            lines.append(f"• [{v}]({folder})")
        lines += ["", f"Ex: `,ngapps {ver} core`"]
        await message.edit("\n".join(lines), disable_web_page_preview=True)
        return
    await message.edit(
        f"📦 **NikGapps {var} — Android {ver}**\n\n"
        f"⬇️ [Pasta da release]({folder})\n"
        f"Arquivo: `NikGapps-{var}-arm64-{ver}-DATA-signed.zip`\n"
        f"(pegue o build de data mais recente)\n\n"
        f"💬 [Canal @NikGapps](https://t.me/NikGapps)",
        disable_web_page_preview=True,
    )
