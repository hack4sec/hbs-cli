# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Integration tests for FinderInsideProThread
"""

import sys
import time
import pytest

sys.path.append('../../')

from libs.common import md5
from classes.FinderInsideProThread import FinderInsideProThread
from CommonIntegration import CommonIntegration

class Test_HashlistsLoaderThread(CommonIntegration):
    """ Integration tests for FinderInsideProThread """
    thrd = None

    def setup(self):
        """ Tests setup """
        self._clean_db()
        self.thrd = FinderInsideProThread()
        self.db.update("algs", {'finder_insidepro_allowed': 1}, "id")


    def teardown(self):
        """ Tests teardown """
        if isinstance(self.thrd, FinderInsideProThread):
            self.thrd.available = False
            time.sleep(1)
            del self.thrd
        self._clean_db()

    test_data = [
        (
            74,
            1,
            [
                {'id': 1, 'hash': '0065ffe5f9e4e5996c2c3f52f81c6e31', 'salt': 'cB6Ar', 'cracked': 1,
                 'summ': md5("0065ffe5f9e4e5996c2c3f52f81c6e31:cB6Ar"), 'password': 'y0007171'},
                {'id': 2, 'hash': '20e153b046072c949562f3c939611db8', 'salt': '0RTV', 'cracked': 0,
                 'summ': md5("20e153b046072c949562f3c939611db8:0RTV"), 'password': ''},
            ]
        ),
        (
            4,
            0,
            [
                {'id': 1, 'hash': md5('aaa'), 'salt': '', 'cracked': 1,
                 'summ': md5(md5('aaa')), 'password': 'aaa'},
                {'id': 2, 'hash': '10e153b046072c949562f3c939611db7', 'salt': '', 'cracked': 0,
                 'summ': md5("10e153b046072c949562f3c939611db7"), 'password': ''},
            ]
        )
    ]
    @pytest.mark.parametrize("alg_id,have_salt,hashes", test_data)
    def test_run(self, alg_id, have_salt, hashes):
        """
        Test simple run
        :param alg_id:
        :param have_salt: does alg has salts?
        :param hashes: Hashes rows
        :return:
        """
        self._add_hashlist(common_by_alg=alg_id, alg_id=alg_id, have_salts=have_salt,
                           last_finder_checked=int(time.time()))
        for _hash in hashes:
            self._add_hash(id=_hash['id'], hash=_hash['hash'], salt=_hash['salt'], summ=_hash['summ'])

        self.thrd.start()

        time.sleep(10)

        assert self.db.fetch_one("SELECT 1 FROM hashes WHERE id = 1 AND cracked = 0 AND password=''") == 1
        assert self.db.fetch_one("SELECT 1 FROM hashes WHERE id = 2 AND cracked = 0 AND password=''") == 1
        assert self.db.fetch_one("SELECT last_finder_checked FROM hashlists WHERE id = 1") < time.time()

        self.db.update("hashlists", {"last_finder_checked": 0}, "id = 1")

        time.sleep(10)

        for _hash in hashes:
            test_data = self.db.fetch_row("SELECT * FROM hashes WHERE id = {0}".format(_hash['id']))
            assert test_data['summ'] == _hash['summ']
            assert test_data['cracked'] == _hash['cracked']
            assert test_data['password'] == _hash['password']

        assert self.db.fetch_one("SELECT last_finder_checked FROM hashlists WHERE id = 1") > time.time() - 20
