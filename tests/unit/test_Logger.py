# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Logger unit tests
"""

import sys
import os
import time

import pytest

sys.path.append('../../')

from CommonUnit import CommonUnit
from classes.Logger import Logger, LoggerException


class Test_HashlistsLoaderThread(CommonUnit):
    """ Logger unit tests """
    thrd = None

    def setup(self):
        """ Setup tests """
        self._clean_db()

    def teardown(self):
        """ Teardown tests """
        self._clean_db()

    def test_log(self):
        logger = Logger()
        with pytest.raises(LoggerException) as ex:
            logger.log('wrong', 'test')
        assert "Module 'wrong' not allowed" in str(ex)

        assert 0 == self.db.fetch_one("SELECT COUNT(id) FROM logs")

        logger.log('main', 'test string')

        assert self.db.fetch_one("SELECT COUNT(id) FROM logs") == 1
        assert self.db.fetch_one("SELECT message FROM logs") == 'test string'
        assert self.db.fetch_one("SELECT module FROM logs") == 'main'
        assert int(self.db.fetch_one("SELECT `timestamp` FROM logs")) > 0