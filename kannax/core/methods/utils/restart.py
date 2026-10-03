# pylint: disable=missing-module-docstring
#
# Copyright (C) 2020-2021 by fnixdev@Github, < https://github.com/fnixdev >.
#
# This file is part of < https://github.com/fnixdev/Kanna-X > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/fnixdev/Kanna-X/blob/master/LICENSE >
#
# All rights reserved.

__all__ = ['Restart']

import os
import sys
import signal

from kannax import logging
from ...ext import RawClient

_LOG = logging.getLogger(__name__)
_LOG_STR = "<<<!  #####  %s  #####  !>>>"


class Restart(RawClient):  # pylint: disable=missing-class-docstring
    async def restart(self, update_req: bool = False,  # pylint: disable=arguments-differ
                      hard: bool = False) -> None:
        """ Restart the Abstract KannaX"""
        _LOG.info(_LOG_STR, "Reiniciando KannaX")
        await self.stop()
        if update_req:
            _LOG.info(_LOG_STR, "Instalando Requirements...")
            os.system(
                "pip3 install -U pip && pip3 install -U -r requirements.txt")
            _LOG.info(_LOG_STR, "Requirements Instalado !")
        if hard:
            os.kill(os.getpid(), signal.SIGUSR1)
        else:
            # NOTE: do NOT close fds here (the old psutil loop closed
            # stdout/stderr/log fds, so the execl'd process died silently
            # during plugin import and ,restart never came back).
            # stop() above already disconnects clients cleanly.
            sys.stdout.flush()
            sys.stderr.flush()
            os.execl(sys.executable, sys.executable, '-m', 'kannax')  # nosec
            sys.exit()
