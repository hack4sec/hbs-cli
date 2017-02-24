# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

HashlistsLoaderThread integration tests
"""

import sys
import time
import pytest

sys.path.append('../../')

from libs.common import md5, file_put_contents
from classes.HashlistsLoaderThread import HashlistsLoaderThread
from CommonIntegration import CommonIntegration

class Test_HashlistsLoaderThread(CommonIntegration):
    """ HashlistsLoaderThread integration tests """
    thrd = None

    def setup(self):
        """ Setup tests """
        self._clean_db()

        self.thrd = HashlistsLoaderThread()
        self.thrd.delay_per_check = 1

    def teardown(self):
        """ Teardown tests """
        if isinstance(self.thrd, HashlistsLoaderThread):
            self.thrd.available = False
            time.sleep(1)
            del self.thrd
        self._clean_db()

    test_data = [
        (
            1,
            'aUNIQUEDELIMITER1\nbUNIQUEDELIMITER2\ncUNIQUEDELIMITER3',
            3,
            [
                {'hash': 'a', 'salt': '1', 'summ': md5('a:1'), 'cracked': 0, 'password': ''},
                {'hash': 'b', 'salt': '2', 'summ': md5('b:2'), 'cracked': 0, 'password': ''},
                {'hash': 'c', 'salt': '3', 'summ': md5('c:3'), 'cracked': 0, 'password': ''},
            ],
            []
        ),
        (
            1,
            'aUNIQUEDELIMITER1\nbUNIQUEDELIMITER2\ncUNIQUEDELIMITER3\n',
            3,
            [
                {'hash': 'a', 'salt': '1', 'summ': md5('a:1'), 'cracked': 0, 'password': ''},
                {'hash': 'b', 'salt': '2', 'summ': md5('b:2'), 'cracked': 0, 'password': ''},
                {'hash': 'c', 'salt': '3', 'summ': md5('c:3'), 'cracked': 0, 'password': ''},
            ],
            []
        ),
        (
            1,
            'aUNIQUEDELIMITER1\nbUNIQUEDELIMITER2\ncUNIQUEDELIMITER3\naUNIQUEDELIMITER1',
            3,
            [
                {'hash': 'a', 'salt': '1', 'summ': md5('a:1'), 'cracked': 0, 'password': ''},
                {'hash': 'b', 'salt': '2', 'summ': md5('b:2'), 'cracked': 0, 'password': ''},
                {'hash': 'c', 'salt': '3', 'summ': md5('c:3'), 'cracked': 0, 'password': ''},
            ],
            []
        ),
        (
            1,
            'aUNIQUEDELIMITER1\nbUNIQUEDELIMITER2\ncUNIQUEDELIMITER3',
            3,
            [
                {'hash': 'a', 'salt': '1', 'summ': md5('a:1'), 'cracked': 1, 'password': 'aaa'},
                {'hash': 'b', 'salt': '2', 'summ': md5('b:2'), 'cracked': 0, 'password': ''},
                {'hash': 'c', 'salt': '3', 'summ': md5('c:3'), 'cracked': 0, 'password': ''},
            ],
            [
                {'hash': 'a', 'salt': '1', 'summ': md5('a:1'), 'cracked': 1, 'password': 'aaa'},
            ]
        ),
        (
            1,
            'aUNIQUEDELIMITERa\\nb\\c\nbUNIQUEDELIMITERa\'b\\c\ncUNIQUEDELIMITERa\\tb\\nc\n',
            3,
            [
                {'hash': 'a', 'salt': 'a\\nb\\c', 'summ': md5('a:a\\nb\\c'), 'cracked': 0, 'password': ''},
                {'hash': 'b', 'salt': 'a\'b\\c', 'summ': md5('b:a\'b\\c'), 'cracked': 0, 'password': ''},
                {'hash': 'c', 'salt': 'a\\tb\\nc', 'summ': md5('c:a\\tb\\nc'), 'cracked': 0, 'password': ''},
            ],
            []
        ),
        (
            0,
            'a\nb\nc',
            3,
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 0, 'password': ''},
                {'hash': 'b', 'salt': '', 'summ': md5('b'), 'cracked': 0, 'password': ''},
                {'hash': 'c', 'salt': '', 'summ': md5('c'), 'cracked': 0, 'password': ''},
            ],
            []
        ),
        (
            0,
            'a\nb\nc\n',
            3,
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 0, 'password': ''},
                {'hash': 'b', 'salt': '', 'summ': md5('b'), 'cracked': 0, 'password': ''},
                {'hash': 'c', 'salt': '', 'summ': md5('c'), 'cracked': 0, 'password': ''},
            ],
            []
        ),
        (
            0,
            'a\nb\nc\na',
            3,
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 0, 'password': ''},
                {'hash': 'b', 'salt': '', 'summ': md5('b'), 'cracked': 0, 'password': ''},
                {'hash': 'c', 'salt': '', 'summ': md5('c'), 'cracked': 0, 'password': ''},
            ],
            []
        ),
        (
            0,
            'a\nb\nc',
            3,
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 1, 'password': 'aaa'},
                {'hash': 'b', 'salt': '', 'summ': md5('b'), 'cracked': 0, 'password': ''},
                {'hash': 'c', 'salt': '', 'summ': md5('c'), 'cracked': 0, 'password': ''},
            ],
            [
                {'hash': 'a', 'salt': '', 'summ': md5('a'), 'cracked': 1, 'password': 'aaa'},
            ]
        ),
    ]
    @pytest.mark.parametrize("have_salts,hashes_content,count_expected,hashes_expected,hashes_found", test_data)
    def test_load_simple_list(self, have_salts, hashes_content, count_expected, hashes_expected, hashes_found):
        """
        Loading simple list in db
        :param have_salts: Does hashlist has salt?
        :param hashes_content: Text content of hashlist
        :param count_expected: How many hashes we expected in db?
        :param hashes_expected: Rows with hashes we expected in db?
        :param hashes_found: Rows with found hashes after load, we expected
        :return:
        """
        self._add_hashlist(have_salts=have_salts, parsed=0, tmp_path='/tmp/1.txt', status='wait')
        file_put_contents('/tmp/1.txt', hashes_content)

        if len(hashes_found):
            self._add_hashlist(id=2, have_salts=have_salts, parsed=1, status='ready')
            for _hash in hashes_found:
                self._add_hash(
                    hashlist_id=2, hash=_hash['hash'], salt=_hash['salt'],
                    password=_hash['password'], cracked=_hash['cracked'], summ=_hash['summ']
                )

        self.thrd.start()
        time.sleep(5)

        assert count_expected == self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hashlist_id = 1")
        for _hash in hashes_expected:
            assert self.db.fetch_one(
                "SELECT COUNT(id) FROM hashes WHERE hashlist_id = 1 "
                "AND hash = {0} AND salt = {1} AND summ = {2} AND password = {3} AND cracked = {4}".
                format(self.db.quote(_hash['hash']), self.db.quote(_hash['salt']), self.db.quote(_hash['summ']),
                       self.db.quote(_hash['password']), _hash['cracked'])
            ) == 1

    def test_add_hashes_to_exists_list(self):
        """ Test adding hashes to exists hashlist """
        self._add_hashlist(parsed=0, tmp_path='/tmp/1.txt', status='wait')
        file_put_contents('/tmp/1.txt', 'c\nd\ne\n', )

        self._add_hash(hash='a')
        self._add_hash(hash='b')
        self._add_hash(hash='c')

        self.thrd.start()
        time.sleep(5)

        assert ['a', 'b', 'c', 'd', 'e'] == \
               self.db.fetch_col("SELECT hash FROM hashes WHERE hashlist_id = 1 ORDER BY hash")

    def test_add_hashes_to_exists_list_with_founds(self):
        """ Testing add hashes to exists list with already found hashes """
        self._add_hashlist(parsed=0, tmp_path='/tmp/1.txt', status='wait')
        file_put_contents('/tmp/1.txt', 'c\nd\ne\n', )

        self._add_hash(hash='a', summ=md5('a'))
        self._add_hash(hash='b', summ=md5('b'))
        self._add_hash(hash='c', summ=md5('c'))

        self._add_hashlist(id=2)
        self._add_hash(hashlist_id=2, hash='a', summ=md5('a'), cracked=1, password='aaa')

        self.thrd.start()
        time.sleep(5)

        assert self.db.fetch_col("SELECT hash FROM hashes WHERE hashlist_id = 1 ORDER BY hash") == \
               ['a', 'b', 'c', 'd', 'e']

        assert self.db.fetch_one("SELECT password FROM hashes "
                                 "WHERE hashlist_id = 1 AND cracked = 1 AND hash = 'a'") == 'aaa'
