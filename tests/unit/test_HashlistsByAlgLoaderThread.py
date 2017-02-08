# -*- coding: utf-8 -*-

import sys
import configparser
import os
import time
import pytest
from pprint import pprint

sys.path.append('../../')

from libs.common import _d, file_get_contents, file_put_contents, md5
from classes.Registry import Registry
from classes.Database import Database
from classes.HashlistsByAlgLoaderThread import HashlistsByAlgLoaderThread
from CommonUnit import CommonUnit

class Test_HashlistsLoaderThread(CommonUnit):
    db = None
    thrd = None

    def setup(self):
        self._clean_db()
        self.thrd = HashlistsByAlgLoaderThread()

    def teardown(self):
        if isinstance(self.thrd, HashlistsByAlgLoaderThread):
            del self.thrd
        self._clean_db()

    def test_get_common_hashlist_id_by_alg_get(self):
        self._add_hashlist(have_salts=1, common_by_alg=3)
        assert 1 == self.thrd._get_common_hashlist_id_by_alg(3)

    def test_get_common_hashlist_id_by_alg_without_salt_create(self):
        assert 1 == self.thrd._get_common_hashlist_id_by_alg(3)

        test_hashlist_data = {'id': 1, 'name': 'All-MD4', 'have_salts': 0, 'delimiter': self.thrd.DELIMITER,
                              'cracked': 0, 'uncracked': 0, 'errors': '', 'parsed': 0, 'status': 'ready',
                              'common_by_alg': 3}
        hashlist_data = self.db.fetch_row("SELECT * FROM hashlists WHERE id = 1")

        for field in test_hashlist_data:
            assert hashlist_data[field] == test_hashlist_data[field]

    def test_get_common_hashlist_id_by_alg_with_salt_create(self):
        self._add_hashlist(have_salts=1, common_by_alg=0)
        self._add_hash(hash='a', salt='b', summ='333')

        assert 2 == self.thrd._get_common_hashlist_id_by_alg(3)

        test_hashlist_data = {'id': 2, 'name': 'All-MD4', 'have_salts': 1, 'delimiter': self.thrd.DELIMITER,
                              'cracked': 0, 'uncracked': 0, 'errors': '', 'parsed': 0, 'status': 'ready',
                              'common_by_alg': 3}
        hashlist_data = self.db.fetch_row("SELECT * FROM hashlists WHERE id = 2")

        for field in test_hashlist_data:
            assert hashlist_data[field] == test_hashlist_data[field]

    def test_get_common_hashlist_id_by_alg_with_salt_create_one_salt_forget(self):
        self._add_hashlist(have_salts=1, common_by_alg=0)
        self._add_hash(hash='a', salt='b', summ='333')

        self._add_hashlist(id=2, have_salts=0, common_by_alg=0)
        self._add_hash(hashlist_id=2, hash='c', salt='d', summ='111')

        assert 3 == self.thrd._get_common_hashlist_id_by_alg(3)

        test_hashlist_data = {'id': 3, 'name': 'All-MD4', 'have_salts': 1, 'delimiter': self.thrd.DELIMITER,
                              'cracked': 0, 'uncracked': 0, 'errors': '', 'parsed': 0, 'status': 'ready',
                              'common_by_alg': 3}
        hashlist_data = self.db.fetch_row("SELECT * FROM hashlists WHERE id = 3")

        for field in test_hashlist_data:
            assert hashlist_data[field] == test_hashlist_data[field]

    def test_get_current_work_hashlist(self):
        assert not self.thrd._get_current_work_hashlist()
        self.db.insert("task_works", {'hashlist_id': 3, 'status': 'work', 'task_id': 1})
        assert 3 == self.thrd._get_current_work_hashlist()

    def test_get_hashlist_status(self):
        self._add_hashlist(common_by_alg=1)
        assert 'ready' == self.thrd._get_hashlist_status(1)

    def test_is_alg_in_parse(self):
        assert False == self.thrd._is_alg_in_parse(3)
        self._add_hashlist(common_by_alg=1)
        self.db.insert("task_works", {'hashlist_id': 1, 'status': 'waitoutparse', 'task_id': 1})
        assert True == self.thrd._is_alg_in_parse(3)

        assert False == self.thrd._is_alg_in_parse(4)
        self._add_hashlist(id=2, alg_id=4, common_by_alg=1)
        self.db.insert("task_works", {'hashlist_id': 2, 'status': 'outparsing', 'task_id': 1})
        assert True == self.thrd._is_alg_in_parse(4)

    def test_hashes_count_in_hashlist(self):
        assert 0 == self.thrd._hashes_count_in_hashlist(1)
        self._add_hash()
        assert 1 == self.thrd._hashes_count_in_hashlist(1)

    def test_hashes_count_by_algs(self):
        assert self.thrd._hashes_count_by_algs() == {}

        self._add_hashlist()
        self._add_hash(summ='111')
        self._add_hash(summ='222', hash='a', salt='b')

        self._add_hashlist(id=2, alg_id=4)
        self._add_hash(hashlist_id=2, summ='333')

        assert self.thrd._hashes_count_by_algs() == {3: 2, 4: 1}

    def test_is_alg_have_salts(self):
        self._add_hashlist()
        assert False == self.thrd._is_alg_have_salts(3)

        self._add_hashlist(id=2, have_salts=1) # Forget salt bug
        assert True == self.thrd._is_alg_have_salts(3)

    def test_get_possible_hashlist_and_alg_simple(self):
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')
        assert {'hashlist_id': 2, 'alg_id': 3} == self.thrd._get_possible_hashlist_and_alg()

    def test_get_possible_hashlist_and_alg_none_already(self):
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        self._add_hashlist(id=2, common_by_alg=3)
        self._add_hash(hashlist_id=2, hash='a', summ='111')
        self._add_hash(hashlist_id=2, hash='b', summ='222')

        assert None == self.thrd._get_possible_hashlist_and_alg()

    def test_get_possible_hashlist_and_alg_none_in_parse(self):
        self.db.insert("task_works", {'hashlist_id': 1, 'status': 'waitoutparse', 'task_id': 1})

        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        assert None == self.thrd._get_possible_hashlist_and_alg()

        self.db.update("task_works", {'status': 'outparsing'}, "id=1")

        assert None == self.thrd._get_possible_hashlist_and_alg()

    def test_get_possible_hashlist_and_alg_none_not_ready(self):
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        self._add_hashlist(id=2, status='wait', common_by_alg=3)

        assert None == self.thrd._get_possible_hashlist_and_alg()

    def test_get_possible_hashlist_and_alg_none_in_work(self):
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        self._add_hashlist(id=2, common_by_alg=3)

        self.db.insert("task_works", {'hashlist_id': 2, 'status': 'work', 'task_id': 1})

        assert None == self.thrd._get_possible_hashlist_and_alg()

    def test_clean_old_hashes(self):
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        assert 2 == self.db.fetch_one("SELECT COUNT(*) FROM hashes WHERE hashlist_id = 1")

        self.thrd._clean_old_hashes(1)

        assert 0 == self.db.fetch_one("SELECT COUNT(*) FROM hashes WHERE hashlist_id = 1")
        assert 0 == self.db.fetch_one("SELECT cracked+uncracked FROM hashlists WHERE id = 1")

    def test_put_all_hashes_of_alg_in_file(self):
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(summ='222')
        self._add_hash(hash='b', summ='333')

        path = self.thrd._put_all_hashes_of_alg_in_file(3)

        assert os.path.exists(path)
        assert file_get_contents(path) == 'a\nb\n'

        self._add_hashlist(id=2, have_salts=1, alg_id=4)
        self._add_hash(hashlist_id=2, hash='a', salt='b', summ='111')
        self._add_hash(hashlist_id=2, summ='222')
        self._add_hash(hashlist_id=2, hash='c', salt='d', summ='333')

        path = self.thrd._put_all_hashes_of_alg_in_file(4)

        assert os.path.exists(path)
        assert file_get_contents(path) == 'a{0}b\nc{0}d\n'.format(self.thrd.DELIMITER)

    def test_simple_one_run(self):
        self._add_hashlist()
        self._add_hash(hash='a', summ='111')
        self._add_hash(hash='b', summ='222')

        assert None == self.db.fetch_one("SELECT id FROM hashlists WHERE common_by_alg")

        self.thrd.start()
        time.sleep(5)

        test_hashlist_data = {'id': 2, 'name': 'All-MD4', 'have_salts': 0, 'delimiter': self.thrd.DELIMITER,
                              'cracked': 0, 'uncracked': 0, 'errors': '', 'parsed': 0, 'status': 'wait',
                              'common_by_alg': 3}
        hashlist_data = self.db.fetch_row("SELECT * FROM hashlists WHERE common_by_alg")

        for field in test_hashlist_data:
            assert hashlist_data[field] == test_hashlist_data[field]



