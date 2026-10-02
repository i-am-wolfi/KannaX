# Gera HU_STRING_SESSION (Pyrogram) para o Kanna-X.
# ATENÇÃO: a STRING_SESSION do CatUserbot é do Telethon e NÃO serve aqui.
# Use o MESMO API_ID / API_HASH do Cat, mas gere uma nova string nesta
# ferramenta (ela usa Pyrogram). Rode: bash genStr   ou   .venv/bin/python tools/genStrSession.py

import asyncio
import sys

sys.path.insert(0, "tools/py314")
import sitecustomize  # noqa: F401  (shim asyncio p/ Python 3.10+)

from pyrogram import Client


def main() -> None:
    print("=== Kanna-X — gerador de HU_STRING_SESSION (Pyrogram) ===")
    print("Use o MESMO API_ID / API_HASH do seu CatUserbot.\n")
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
