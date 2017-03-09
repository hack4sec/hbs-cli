# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Logging in db
"""
import time
import sys

from classes.Registry import Registry
from classes.Factory import Factory
from libs.common import file_put_contents


class LoggerException(Exception):
    """ Logger exception class """
    pass


class Logger(object):
    """ Class of logger in db """
    _db = None  # type: Database

    allowed_modules = [
        'database',
        'finderinsidepro',
        'hashlist_common_loader',
        'hashlist_loader',
        'result_parser',
        'worker',
        'main',
    ]

    def __init__(self):
        self._db = Factory().new_db_connect()

    def log(self, module, message):
        """
        Log message from hbs
        :param module:
        :param message:
        :return:
        """
        if module not in Logger.allowed_modules:
            raise LoggerException("Module '{0}' not allowed".format(module))

        print "[{0}][{1}] {2}".format(
            time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
            module.upper(),
            message.strip()
        )
        sys.stdout.flush()

        self._db.insert(
            "logs",
            {
                "module": module,
                "timestamp": int(time.time()),
                "message": message,
            }
        )
