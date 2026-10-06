# Gera HU_STRING_SESSION (Pyrogram) para o Kanna-X.
# Roda no pyrogram v2 (venv isolada .venv-genstr): o 1.4.16 do bot é
# bloqueado pelo Telegram em logins novos (406 UPDATE_APP_TO_LOGIN).
# A string gerada aqui serve no 1.4.16 normalmente.
# Use seu API_ID / API_HASH do https://my.telegram.org.
# Rode: bash run-genstr.sh

import asyncio
import base64
import os
import struct

from pyrogram import Client


def _to_v1_string(session: str) -> str:
    """Converte string do pyrogram v2 (362 chars) p/ formato 1.4 (356).

    v2 empacota ">BI?256sQ?" (271 bytes); 1.4 lê ">B?256sQ?" (267 bytes)
    quando o user_id passa de 32 bits. Reempacota preservando
    dc_id, test_mode, auth_key, user_id e is_bot.
    """
    session = session.strip()
    if len(session) in (351, 356):
        return session  # já é formato 1.4
    raw = base64.urlsafe_b64decode(session + "=" * (-len(session) % 4))
    if len(raw) == 271:  # >BI?256sQ?
        dc_id, _old, test_mode, auth_key, user_id, is_bot = struct.unpack(">BI?256sQ?", raw)
        packed = struct.pack(">B?256sQ?", dc_id, test_mode, auth_key, user_id, is_bot)
    else:
        raise RuntimeError(f"formato de string desconhecido ({len(session)} chars).")
    out = base64.urlsafe_b64encode(packed).decode().rstrip("=")
    if len(out) not in (351, 356):
        raise RuntimeError("conversão falhou, tente de novo.")
    return out


def main() -> None:
    print("=== Kanna-X — gerador de HU_STRING_SESSION (Pyrogram) ===")
    print("Pegue seu API_ID / API_HASH em https://my.telegram.org\n")
    api_id = int(input("Enter API_ID: ").strip())
    api_hash = input("Enter API_HASH: ").strip()

    async def _gen() -> str:
        # sessão com nome único por tentativa: nada é reaproveitado
        # (sessão parcial reutilizada = AUTH_KEY_UNREGISTERED certo)
        import time as _t

        last_err = None
        for attempt in range(2):
            sess = f"genstr_{os.getpid()}_{attempt}_{int(_t.time())}"
            try:
                async with Client(sess, api_id=api_id, api_hash=api_hash) as app:
                    me = await app.get_me()
                    print(f"Logado como: {me.first_name} (id={me.id})")
                    session = await app.export_session_string()
                    session = _to_v1_string(session.strip())
                    await app.send_message(
                        "me",
                        f"#KannaX #HU_STRING_SESSION\n\n`{session}`\n\nCole no config.env como HU_STRING_SESSION.",
                    )
                    return session
            except Exception as e:
                last_err = e
                if "AUTH_KEY_UNREGISTERED" not in type(e).__name__ and "AUTH_KEY_UNREGISTERED" not in str(e):
                    raise
                print(f"Tentativa {attempt + 1} falhou (chave parcial), tentando de novo...")
            finally:
                for f in (sess + ".session", sess + ".session-journal"):
                    try:
                        os.remove(f)
                    except OSError:
                        pass
        raise last_err

    session = asyncio.run(_gen())
    print("\nPronto! Sua HU_STRING_SESSION (cole no config.env):\n")
    print(session)
    print("\nUma cópia/aviso também foi enviada para suas Mensagens Salvas.")


if __name__ == "__main__":
    main()
