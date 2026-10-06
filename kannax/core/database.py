# pylint: disable=missing-module-docstring
#
# Copyright (C) 2020 by UsergeTeam@Github, < https://github.com/UsergeTeam >.
#
# Editado por fnixdev

__all__ = ['get_collection']

import asyncio
import os
from typing import List

from motor.motor_asyncio import AsyncIOMotorClient
from motor.core import AgnosticClient, AgnosticDatabase, AgnosticCollection

from kannax import logging, Config, logbot

_LOG = logging.getLogger(__name__)
_LOG_STR = "$$$>>> %s <<<$$$"

logbot.edit_last_msg("Conectando-se a Database ...", _LOG.info, _LOG_STR)


def _direct_mongo_uri(uri: str) -> str:
    """Rewrite mongodb+srv:// to direct mongodb:// on systems without
    /etc/resolv.conf (Termux): pymongo's SRV lookup reads resolv.conf
    and dies with 'cannot open /etc/resolv.conf'. Plain hostnames
    resolve fine via libc, so resolve SRV+T SVD once here with an
    explicit nameserver and bake the hosts into the URI.
    """
    if not uri.startswith("mongodb+srv://") or os.access("/etc/resolv.conf", os.R_OK):
        return uri
    try:
        from urllib.parse import urlsplit, urlunsplit
        import dns.resolver
    except ImportError as e:
        raise RuntimeError(f"mongo+srv sem resolv.conf e sem dnspython: {e}")
    parts = urlsplit(uri)
    host = parts.hostname or ""
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
    answers = resolver.resolve(f"_mongodb._tcp.{host}", "SRV")
    hosts = sorted(
        {f"{str(r.target).rstrip('.')}:{r.port}" for r in answers},
        key=lambda h: h,
    )
    if not hosts:
        raise RuntimeError(f"SRV vazio para {host}")
    try:
        txt = resolver.resolve(host, "TXT")
        opts = "&".join(
            s.decode().strip('"') for r in txt for s in r.strings
        )
    except Exception:
        opts = ""
    query = "&".join(q for q in [parts.query, opts] if q)
    if "tls=" not in query and "ssl=" not in query:
        # +srv implica TLS; sem isso o Atlas derruba a conexão
        query = (query + "&" if query else "") + "tls=true"
    auth = ""
    if parts.username:
        auth = parts.username
        if parts.password:
            auth += f":{parts.password}"
        auth += "@"
    path = parts.path or "/"
    return urlunsplit(("mongodb", f"{auth}{','.join(hosts)}", path, query, ""))


_MGCLIENT: AgnosticClient = AsyncIOMotorClient(_direct_mongo_uri(Config.DB_URI))
_RUN = asyncio.get_event_loop().run_until_complete

if "KannaX" in _RUN(_MGCLIENT.list_database_names()):
    _LOG.info(_LOG_STR, "Banco de dados KannaX encontrado :) => Agora logando nele...")
else:
    _LOG.info(_LOG_STR, "Banco de dados KannaX não encontrado :( => Criando nova Database...")

_DATABASE: AgnosticDatabase = _MGCLIENT["KannaX"]
_COL_LIST: List[str] = _RUN(_DATABASE.list_collection_names())


def get_collection(name: str) -> AgnosticCollection:
    """ Criar ou obter coleção de seu banco de dados """
    if name in _COL_LIST:
        _LOG.debug(_LOG_STR, f"{name} Coleção encontrada :) => Agora logando nela...")
    else:
        _LOG.debug(_LOG_STR, f"{name} Coleção não encontrada :( => Criando nova coleção...")
    return _DATABASE[name]


def _close_db() -> None:
    _MGCLIENT.close()


logbot.del_last_msg()
