# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Integration tests for HashlistsByAlgLoaderThread
"""
import sys
import time
import pytest

sys.path.append('../../')

from libs.common import md5
from classes.HashlistsByAlgLoaderThread import HashlistsByAlgLoaderThread
from classes.HashlistsLoaderThread import HashlistsLoaderThread
from CommonIntegration import CommonIntegration

class Test_HashlistsByAlgLoaderThread(CommonIntegration):
    """ Class of integration tests - HashlistsByAlgLoaderThread """
    thrd = None
    loader_thrd = None

    def setup(self):
        """ Tests setup """
        self._clean_db()

        self.thrd = HashlistsByAlgLoaderThread()
        self.thrd.delay_per_check = 1

        self.loader_thrd = HashlistsLoaderThread()
        self.loader_thrd.delay_per_check = 1

    def teardown(self):
        """ Tests teardown """
        if isinstance(self.thrd, HashlistsByAlgLoaderThread):
            self.thrd.available = False
            time.sleep(1)
            del self.thrd
        if isinstance(self.loader_thrd, HashlistsLoaderThread):
            self.loader_thrd.available = False
            time.sleep(1)
            del self.loader_thrd
        self._clean_db()

    test_data = [
        (
            [
                {'hash': 'a', 'salt': '\\ta\'1\\', 'summ': md5('a:\\ta\'1\\')},
                {'hash': 'b', 'salt': '\\nb"2\\', 'summ': md5('b:\\nb"2\\')}
            ],
            1
        ),
        (
            [
                {'hash': 'a', 'salt': '1', 'summ': md5('a:1')},
                {'hash': 'b', 'salt': '2', 'summ': md5('b:2')}
            ],
            1
        ),
        (
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a')},
                {'hash': 'b', 'salt': '', 'summ': md5('b')}
            ],
            0
        ),
    ]
    @pytest.mark.parametrize("hashes,have_salt", test_data)
    def test_simple_build(self, hashes, have_salt):
        """
        Simple common hashlist build
        :param hashes: hashes rows
        :param have_salt: Does alg has salt?
        :return:
        """
        self._add_hashlist(have_salts=have_salt)
        for _hash in hashes:
            self._add_hash(hash=_hash['hash'], salt=_hash['salt'], summ=_hash['summ'])

        assert self.db.fetch_one("SELECT id FROM hashlists WHERE common_by_alg") is None

        self.thrd.start()
        self.loader_thrd.start()
        time.sleep(5)

        test_hashlist_data = {'id': 2, 'name': 'All-MD4', 'have_salts': have_salt, 'delimiter': self.thrd.DELIMITER,
                              'cracked': 0, 'uncracked': 2, 'errors': '', 'parsed': 1, 'status': 'ready',
                              'common_by_alg': 3}
        hashlist_data = self.db.fetch_row("SELECT * FROM hashlists WHERE common_by_alg")

        for field in test_hashlist_data:
            assert hashlist_data[field] == test_hashlist_data[field]

        for _hash in hashes:
            assert self.db.fetch_one(
                "SELECT COUNT(id) FROM hashes WHERE hash = {0} AND salt={1} AND summ = {2} AND hashlist_id = 2".
                format(self.db.quote(_hash['hash']), self.db.quote(_hash['salt']), self.db.quote(_hash['summ']))
            ) == 1

    test_data = [
        (
            [
                {'hash': 'a', 'salt': '1', 'summ': md5('a:1'), 'cracked': 0},
                {'hash': 'b', 'salt': '2', 'summ': md5('b:2'), 'cracked': 1},
                {'hash': 'c', 'salt': '3', 'summ': md5('c:3'), 'cracked': 0},
                {'hash': 'd', 'salt': '4', 'summ': md5('d:4'), 'cracked': 0},
            ],
            [
                {'hash': 'a', 'salt': '1', 'summ': md5('a:1'), 'cracked': 0},
                {'hash': 'b', 'salt': '2', 'summ': md5('b:2'), 'cracked': 0},
            ],
            1
        ),
        (
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 0},
                {'hash': 'b', 'salt': '', 'summ': md5('b'), 'cracked': 1},
                {'hash': 'c', 'salt': '', 'summ': md5('c'), 'cracked': 0},
                {'hash': 'd', 'salt': '', 'summ': md5('d'), 'cracked': 0},
            ],
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 0},
                {'hash': 'b', 'salt': '', 'summ': md5('b'), 'cracked': 0},
            ],
            0
        ),
    ]
    @pytest.mark.parametrize("hashes_in_self,hashes_in_common,have_salt", test_data)
    def test_update_exists_list(self, hashes_in_self, hashes_in_common, have_salt):
        """
        Updating exists common hashlist
        :param hashes_in_self: Hashes in usual hashlist
        :param hashes_in_common: Hashes in common hashlist
        :param have_salt: Does alg has salt?
        :return:
        """
        self._add_hashlist(have_salts=have_salt)
        for _hash in hashes_in_self:
            self._add_hash(hash=_hash['hash'], salt=_hash['salt'], summ=_hash['summ'], cracked=_hash['cracked'])

        self._add_hashlist(id=2, alg_id=3, common_by_alg=3, have_salts=have_salt)
        for _hash in hashes_in_common:
            self._add_hash(
                hashlist_id=2, hash=_hash['hash'], salt=_hash['salt'], summ=_hash['summ'], cracked=_hash['cracked']
            )

        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='b'") == 2
        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='c'") == 1
        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='d'") == 1

        self.thrd.start()
        self.loader_thrd.start()

        time.sleep(5)

        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='b'") == 1
        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='c'") == 2
        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='d'") == 2

        assert [{'hash': 'a'}, {'hash': 'c'}, {'hash': 'd'}] \
               == self.db.fetch_all("SELECT hash FROM hashes WHERE hashlist_id = 2")

    test_data = [('outparsing'), ('waitoutparse')]
    @pytest.mark.parametrize("status", test_data)
    def test_build_with_parsing_alg(self, status):
        """
        Try build no ready hashlist
        :param status:
        :return:
        """
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        self._add_hashlist(id=2, alg_id=3, common_by_alg=0)

        self._add_work_task(hashlist_id=2, status=status)

        assert self.db.fetch_one("SELECT id FROM hashlists WHERE common_by_alg") is None

        self.thrd.start()
        self.loader_thrd.start()
        time.sleep(5)

        assert self.db.fetch_one("SELECT id FROM hashlists WHERE common_by_alg") is None

        self.db.update("task_works", {'status': 'wait'}, 'id=1')

        time.sleep(5)

        test_hashlist_data = {'id': 3, 'name': 'All-MD4', 'have_salts': 0, 'delimiter': self.thrd.DELIMITER,
                              'cracked': 0, 'uncracked': 2, 'errors': '', 'parsed': 1, 'status': 'ready',
                              'common_by_alg': 3}
        hashlist_data = self.db.fetch_row("SELECT * FROM hashlists WHERE common_by_alg")

        for field in test_hashlist_data:
            assert hashlist_data[field] == test_hashlist_data[field]

        assert self.db.fetch_all("SELECT hash FROM hashes WHERE hashlist_id = 3") == [{'hash': 'a'}, {'hash': 'b'}]
