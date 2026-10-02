#!/bin/bash
#
# Copyright (C) 2020 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
#
# Editado por fnixdev

urlEncode() {
    # (corrigido p/ curl 8.x: a forma antiga passava URL vazia "" e falhava,
    #  gerando texto vazio e erro 400 do Telegram. Usa python3 agora.)
    local raw="${1#\~}"
    raw=$(sed -E 's/(\\t)|(\\n)/ /g' <<< "$raw")
    echo "<code>$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.stdin.read()), end="")' <<< "$raw")</code>"
}
