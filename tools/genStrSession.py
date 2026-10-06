# Gera HU_STRING_SESSION (Pyrogram) para o Kanna-X.
# Roda no pyrogram v2 (venv isolada .venv-genstr): o 1.4.16 do bot é
# bloqueado pelo Telegram em logins novos (406 UPDATE_APP_TO_LOGIN).
# A string gerada aqui serve no 1.4.16 normalmente.
# Use seu API_ID / API_HASH do https://my.telegram.org.
# Rode: bash run-genstr.sh

import asyncio

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

    session = asyncio.run(_gen())
    print("\nPronto! Sua HU_STRING_SESSION (cole no config.env):\n")
    print(session)
    print("\nUma cópia/aviso também foi enviada para suas Mensagens Salvas.")


if __name__ == "__main__":
    main()
