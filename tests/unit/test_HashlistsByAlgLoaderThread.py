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
import os
import time

import pytest

sys.path.append('../../')

from libs.common import file_get_contents, md5
from classes.HashlistsByAlgLoaderThread import HashlistsByAlgLoaderThread
from CommonUnit import CommonUnit

class Test_HashlistsByAlgLoaderThread(CommonUnit):
    """ Unit tests for HashlistsByAlgLoaderThread """
    db = None
    thrd = None

    def setup(self):
        """ Tests setup """
        self._clean_db()
        self.thrd = HashlistsByAlgLoaderThread()
        self.thrd.catch_exceptions = False

    def teardown(self):
        """ Tests teardown """
        if isinstance(self.thrd, HashlistsByAlgLoaderThread):
            self.thrd.available = False
            time.sleep(1)
            del self.thrd
        self._clean_db()

    def test_get_common_hashlist_id_by_alg_get(self):
        """ Test get_common_hashlist_id_by_alg_get() """
        self._add_hashlist(have_salts=1, common_by_alg=3)
        assert self.thrd.get_common_hashlist_id_by_alg(3) == 1

    test_data = [
        (
            1,
            {'hash': 'a', 'salt': '1', 'summ': md5('a:1')},
        ),
        (
            0,
            {'hash': 'a', 'salt': '', 'summ': md5('a')},
        ),
    ]
    @pytest.mark.parametrize("have_salt,_hash", test_data)
    def test_get_common_hashlist_id_by_alg_create(self, have_salt, _hash):
        """
        Test get_common_hashlist_id_by_alg_create()
        :param have_salt: does hashlist has salt?
        :param _hash: hash data row
        :return:
        """
        self._add_hashlist(have_salts=have_salt, common_by_alg=0)
        self._add_hash(hash=_hash['hash'], salt=_hash['salt'], summ=_hash['summ'])

        assert self.thrd.get_common_hashlist_id_by_alg(3) == 2

        test_hashlist_data = {'id': 2, 'name': 'All-MD4', 'have_salts': have_salt, 'delimiter': self.thrd.DELIMITER,
                              'cracked': 0, 'uncracked': 0, 'errors': '', 'parsed': 0, 'status': 'ready',
                              'common_by_alg': 3}
        hashlist_data = self.db.fetch_row("SELECT * FROM hashlists WHERE id = 2")

        for field in test_hashlist_data:
            assert hashlist_data[field] == test_hashlist_data[field]

    def test_get_common_hashlist_id_by_alg_with_salt_create_one_salt_forget(self):
        """ Test get_common_hashlist_id_by_alg_create() """
        self._add_hashlist(have_salts=1, common_by_alg=0)
        self._add_hash(hash='a', salt='b', summ='333')

        self._add_hashlist(id=2, have_salts=0, common_by_alg=0)
        self._add_hash(hashlist_id=2, hash='c', salt='d', summ='111')

        assert self.thrd.get_common_hashlist_id_by_alg(3) == 3

        test_hashlist_data = {'id': 3, 'name': 'All-MD4', 'have_salts': 1, 'delimiter': self.thrd.DELIMITER,
                              'cracked': 0, 'uncracked': 0, 'errors': '', 'parsed': 0, 'status': 'ready',
                              'common_by_alg': 3}
        hashlist_data = self.db.fetch_row("SELECT * FROM hashlists WHERE id = 3")

        for field in test_hashlist_data:
            assert hashlist_data[field] == test_hashlist_data[field]

    def test_get_current_work_hashlist(self):
        """ Test get_current_work_hashlist() """
        assert not self.thrd.get_current_work_hashlist()
        self.db.insert("task_works", {'hashlist_id': 3, 'status': 'work', 'task_id': 1})
        assert self.thrd.get_current_work_hashlist() == 3

    def test_get_hashlist_status(self):
        """ Test get_hashlist_status() """
        self._add_hashlist(common_by_alg=1)
        assert self.thrd.get_hashlist_status(1) == 'ready'

    def test_is_alg_in_parse(self):
        """ Test is_alg_in_parse() """
        assert self.thrd.is_alg_in_parse(3) is False
        self._add_hashlist(common_by_alg=1)
        self.db.insert("task_works", {'hashlist_id': 1, 'status': 'waitoutparse', 'task_id': 1})
        assert self.thrd.is_alg_in_parse(3) is True

        assert self.thrd.is_alg_in_parse(4) is False
        self._add_hashlist(id=2, alg_id=4, common_by_alg=1)
        self.db.insert("task_works", {'hashlist_id': 2, 'status': 'outparsing', 'task_id': 1})
        assert self.thrd.is_alg_in_parse(4) is True

    def test_hashes_count_in_hashlist(self):
        """ Test hashes_count_in_hashlist() """
        assert self.thrd.hashes_count_in_hashlist(1) == 0
        self._add_hash()
        assert self.thrd.hashes_count_in_hashlist(1) == 1

    def test_hashes_count_by_algs(self):
        """ Test hashes_count_by_algs() """
        assert self.thrd.hashes_count_by_algs() == {}

        self._add_hashlist()
        self._add_hash(summ='111')
        self._add_hash(summ='222', hash='a', salt='b')

        self._add_hashlist(id=2, alg_id=4)
        self._add_hash(hashlist_id=2, summ='333')

        assert self.thrd.hashes_count_by_algs() == {3: 2, 4: 1}

    def test_is_alg_have_salts(self):
        """ Test is_alg_have_salts() """
        self._add_hashlist()
        assert self.thrd.is_alg_have_salts(3) is False

        self._add_hashlist(id=2, have_salts=1) # Forget salt bug
        assert self.thrd.is_alg_have_salts(3) is True

    def test_get_possible_hashlist_and_alg_simple(self):
        """ Test get_possible_hashlist_and_alg_simple() """
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')
        assert self.thrd.get_possible_hashlist_and_alg() == {'hashlist_id': 2, 'alg_id': 3}

    def test_get_possible_hashlist_and_alg_none_already(self):
        """ Test get_possible_hashlist_and_alg_none_already() """
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        self._add_hashlist(id=2, common_by_alg=3)
        self._add_hash(hashlist_id=2, hash='a', summ='111')
        self._add_hash(hashlist_id=2, hash='b', summ='222')

        assert self.thrd.get_possible_hashlist_and_alg() is None

    def test_get_possible_hashlist_and_alg_none_in_parse(self):
        """ Test get_possible_hashlist_and_alg_none_in_parse() """
        self.db.insert("task_works", {'hashlist_id': 1, 'status': 'waitoutparse', 'task_id': 1})

        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        assert self.thrd.get_possible_hashlist_and_alg() is None

        self.db.update("task_works", {'status': 'outparsing'}, "id=1")

        assert self.thrd.get_possible_hashlist_and_alg() is None

    def test_get_possible_hashlist_and_alg_none_not_ready(self):
        """ Test get_possible_hashlist_and_alg_none_not_ready() """
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        self._add_hashlist(id=2, status='wait', common_by_alg=3)

        assert self.thrd.get_possible_hashlist_and_alg() is None

    def test_get_possible_hashlist_and_alg_none_in_work(self):
        """ Test get_possible_hashlist_and_alg_none_in_work() """
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        self._add_hashlist(id=2, common_by_alg=3)

        self.db.insert("task_works", {'hashlist_id': 2, 'status': 'work', 'task_id': 1})

        assert self.thrd.get_possible_hashlist_and_alg() is None

    def test_clean_old_hashes(self):
        """ Test clean_old_hashes() """
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        assert self.db.fetch_one("SELECT COUNT(*) FROM hashes WHERE hashlist_id = 1") == 2

        self.thrd.clean_old_hashes(1)

        assert self.db.fetch_one("SELECT COUNT(*) FROM hashes WHERE hashlist_id = 1") == 0
        assert self.db.fetch_one("SELECT cracked+uncracked FROM hashlists WHERE id = 1") == 0

    def test_put_all_hashes_of_alg_in_file(self):
        """ Test put_all_hashes_of_alg_in_file() """
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(summ='222')
        self._add_hash(hash='b', summ='333')

        path = self.thrd.put_all_hashes_of_alg_in_file(3)

        assert os.path.exists(path)
        assert file_get_contents(path) == 'a\nb\n'

        self._add_hashlist(id=2, have_salts=1, alg_id=4)
        self._add_hash(hashlist_id=2, hash='a', salt='b', summ='111')
        self._add_hash(hashlist_id=2, summ='222')
        self._add_hash(hashlist_id=2, hash='c', salt='d', summ='333')

        path = self.thrd.put_all_hashes_of_alg_in_file(4)

        assert os.path.exists(path)
        assert file_get_contents(path) == 'a{0}b\nc{0}d\n'.format(self.thrd.DELIMITER)
