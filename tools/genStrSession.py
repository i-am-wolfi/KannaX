# Gera HU_STRING_SESSION (Pyrogram) para o Kanna-X.
# ATENÇÃO: strings do Telethon (ex: de outros userbots) NÃO servem aqui.
# Use seu API_ID / API_HASH do https://my.telegram.org.
# Rode: bash run-genstr.sh

import asyncio
import sys

sys.path.insert(0, "tools/py314")
import sitecustomize  # noqa: F401  (shim asyncio p/ Python 3.10+)

from pyrogram import Client


def main() -> None:
    print("=== Kanna-X — gerador de HU_STRING_SESSION (Pyrogram) ===")
    print("Pegue seu API_ID / API_HASH em https://my.telegram.org\n")
    api_id = int(input("Enter API_ID: ").strip())
    api_hash = input("Enter API_HASH: ").strip()

    async def _gen() -> str:
        async with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
            await app.send_message(
                "me", "#KannaX #HU_STRING_SESSION\n\nA sua string vai aparecer no terminal."
            )
            return await app.export_session_string()

    session = asyncio.get_event_loop().run_until_complete(_gen())
    print("\nPronto! Sua HU_STRING_SESSION (cole no config.env):\n")
    print(session)
    print("\nUma cópia/aviso também foi enviada para suas Mensagens Salvas.")


if __name__ == "__main__":
    main()
