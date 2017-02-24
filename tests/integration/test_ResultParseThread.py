# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Class of integration tests for WorkerThread
"""

import sys
import time
import pytest

sys.path.append('../../')

from libs.common import md5, file_put_contents
from classes.ResultParseThread import ResultParseThread
from CommonIntegration import CommonIntegration

class Test_ResultParseThread(CommonIntegration):
    """ Class of integration tests for WorkerThread """
    thrd = None
    loader_thrd = None

    def setup(self):
        """ Setup tests """
        self._clean_db()
        self.thrd = ResultParseThread()

    def teardown(self):
        """ Teardown tests """
        if isinstance(self.thrd, ResultParseThread):
            self.thrd.available = False
            time.sleep(1)
            del self.thrd
        self._clean_db()

    test_data = [
        (
            0,
            'a:{0}\nb:{1}\nc:{2}'.format('1'.encode('hex'), '2'.encode('hex'), '3'.encode('hex')),
            2,
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 0, 'password': '1'},
                {'hash': 'b', 'salt': '', 'summ': md5('b'), 'cracked': 0, 'password': '2'},
                {'hash': 'c', 'salt': '', 'summ': md5('WRONG'), 'cracked': 0, 'password': ''},
            ]
        ),
        (
            0,
            'a:{0}\nb:{1}\nc:{2}\n'.format('1'.encode('hex'), '2'.encode('hex'), '3'.encode('hex')),
            2,
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 0, 'password': '1'},
                {'hash': 'b', 'salt': '', 'summ': md5('b'), 'cracked': 0, 'password': '2'},
                {'hash': 'c', 'salt': '', 'summ': md5('WRONG'), 'cracked': 0, 'password': ''},
            ]
        ),
        (
            0,
            'a:{0}\nb:{1}\nc:{2}\na:{0}'.format('1'.encode('hex'), '2'.encode('hex'), '3'.encode('hex')),
            2,
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 0, 'password': '1'},
                {'hash': 'b', 'salt': '', 'summ': md5('b'), 'cracked': 0, 'password': '2'},
                {'hash': 'c', 'salt': '', 'summ': md5('WRONG'), 'cracked': 0, 'password': ''},
            ]
        ),
        (
            1,
            'a:x:{0}\nb:y:{1}\nc:{2}'.format('1'.encode('hex'), '2'.encode('hex'), '3'.encode('hex')),
            2,
            [
                {'hash': 'a', 'salt': 'x', 'summ': md5('a:x'), 'cracked': 0, 'password': '1'},
                {'hash': 'b', 'salt': 'y', 'summ': md5('b:y'), 'cracked': 0, 'password': '2'},
                {'hash': 'c', 'salt': 'z', 'summ': md5('c:WRONG'), 'cracked': 0, 'password': ''},
            ]
        ),
        (
            1,
            'a:x\'"\\a:{0}\nb:y\\ng\\t:{1}\nc:{2}'.format('1'.encode('hex'), '2'.encode('hex'), '3'.encode('hex')),
            2,
            [
                {'hash': 'a', 'salt': 'x\'"\\a', 'summ': md5('a:x\'"\\a'), 'cracked': 0, 'password': '1'},
                {'hash': 'b', 'salt': 'y\\ng\\t', 'summ': md5('b:y\\ng\\t'), 'cracked': 0, 'password': '2'},
                {'hash': 'c', 'salt': 'z', 'summ': md5('c:WRONG'), 'cracked': 0, 'password': ''},
            ]
        )
    ]
    @pytest.mark.parametrize("have_salts,out_content,expected_cracked_count,hashes", test_data)
    def test_simple_out(self, have_salts, out_content, expected_cracked_count, hashes):
        """ Parse simple outfile """
        file_put_contents('/tmp/1.txt', out_content)

        self._add_hashlist(have_salts=have_salts)
        self._add_work_task(out_file='/tmp/1.txt', status='waitoutparse')
        self._add_task()

        for _hash in hashes:
            self._add_hash(hash=_hash['hash'], salt=_hash['salt'], summ=_hash['summ'], cracked=_hash['cracked'])

        self.thrd.start()
        time.sleep(5)

        assert self.db.fetch_one("SELECT status FROM task_works WHERE id = 1") == 'done'
        assert len(hashes) - expected_cracked_count == self.db.fetch_one(
            "SELECT uncracked_after FROM task_works WHERE id = 1")

        for _hash in hashes:
            assert _hash['password'] == self.db.fetch_one(
                "SELECT password FROM hashes WHERE hash = {0}".format(self.db.quote(_hash['hash'])))
