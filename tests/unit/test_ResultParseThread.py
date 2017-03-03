# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Class of unit tests for WorkerThread
"""

import sys
import time
import pytest

sys.path.append('../../')

from libs.common import file_put_contents
from classes.ResultParseThread import ResultParseThread
from classes.HbsException import HbsException
from CommonUnit import CommonUnit

class Test_ResultParseThread(CommonUnit):
    """ Class of unit tests for WorkerThread """
    thrd = None

    def setup(self):
        """ Setup tests """
        self._clean_db()
        self._add_work_task()
        self.thrd = ResultParseThread()
        self.thrd.current_work_task_id = 1
        self.thrd.catch_exceptions = False

    def teardown(self):
        """ Teardown tests """
        if isinstance(self.thrd, ResultParseThread):
            self.thrd.available = False
            time.sleep(1)
            del self.thrd
        self._clean_db()

    def test_update_status(self):
        """ Testing  update_status() method """
        self._add_work_task(id=2)
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=1") == 'wait'
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=2") == 'wait'
        self.thrd.update_status('done')
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=1") == 'done'
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=2") == 'wait'

    def test_get_work_task_data(self):
        """ Testing  get_work_task_data() method """
        data1 = self.thrd.get_work_task_data()
        test_data1 = {'id': 1, 'task_id': 1, 'hashlist_id': 1, 'status': 'wait'}
        for field in test_data1:
            assert data1[field] == test_data1[field]

        self._add_work_task(id=2, hashlist_id=3, task_id=4, status='outparsing')

        self.thrd.current_work_task_id = 1
        data2 = self.thrd.get_work_task_data()
        test_data2 = {'id': 2, 'task_id': 4, 'hashlist_id': 3, 'status': 'outparsing'}
        for field in test_data2:
            assert data2[field] == test_data1[field]

    def test_update_work_task_field(self):
        """ Testing update_work_task_field() method """
        self.thrd.update_work_task_field('status', 'done')
        self.thrd.update_work_task_field('hashlist_id', '2')
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=1") == 'done'
        assert self.db.fetch_one("SELECT hashlist_id FROM task_works WHERE id=1") == 2

    def test_update_all_hashlists_counts(self):
        """ Test of update_all_hashlists_counts() """
        self._add_hashlist()
        self._add_hash(hash='a')
        self._add_hash(hash='b', cracked=1, password='1')

        self._add_hashlist(id=2)
        self._add_hash(hashlist_id=2, hash='a')
        self._add_hash(hashlist_id=2, hash='b')
        self._add_hash(hashlist_id=2, hash='c', cracked=1, password='1')

        self._add_hashlist(id=3)
        self._add_hash(hashlist_id=3, hash='a')
        self._add_hash(hashlist_id=3, hash='b')
        self._add_hash(hashlist_id=3, hash='c')
        self._add_hash(hashlist_id=3, hash='d')
        self._add_hash(hashlist_id=3, hash='e', cracked=1, password='2')
        self._add_hash(hashlist_id=3, hash='f', cracked=1, password='3')

        self.thrd.update_all_hashlists_counts_by_alg_id(3)

        assert self.db.fetch_one("SELECT uncracked FROM hashlists WHERE id=1") == 1
        assert self.db.fetch_one("SELECT cracked FROM hashlists WHERE id=1") == 1

        assert self.db.fetch_one("SELECT uncracked FROM hashlists WHERE id=2") == 2
        assert self.db.fetch_one("SELECT cracked FROM hashlists WHERE id=2") == 1

        assert self.db.fetch_one("SELECT uncracked FROM hashlists WHERE id=3") == 4
        assert self.db.fetch_one("SELECT cracked FROM hashlists WHERE id=3") == 2

    def test_get_current_work_task(self):
        """ Test of get_current_work_task() """
        assert self.thrd.get_current_work_task_id() == 1

        self.thrd.current_work_task_id = 2
        assert self.thrd.get_current_work_task_id() == 2

        with pytest.raises(HbsException) as ex:
            self.thrd.current_work_task_id = None
            self.thrd.get_current_work_task_id()
        assert "Current task for work not set" in str(ex)

    def test_get_waiting_task_for_work(self):
        """ Test of get_waiting_task_for_work() """
        self._add_work_task(id=2, status='waitoutparse')
        assert self.thrd.get_waiting_task_for_work() == 2
        assert self.thrd.current_work_task_id == 2

        self.db.update("task_works", {'status': 'waitoutparse'}, "id = 1")
        assert self.thrd.get_waiting_task_for_work() == 1
        assert self.thrd.current_work_task_id == 1

        self.db.q("UPDATE task_works SET status = 'wait'")
        self.thrd.get_waiting_task_for_work()
        with pytest.raises(HbsException) as ex:
            self.thrd.get_current_work_task_id()
        assert "Current task for work not set" in str(ex)
        assert self.thrd.current_work_task_id is None

    def test_get_hashlist_data(self):
        """ Test of get_hashlist_data() """
        self._add_hashlist()
        assert self.db.fetch_row("SELECT * FROM hashlists WHERE id = 1") == self.thrd.get_hashlist_data(1)
        assert self.thrd.get_hashlist_data(33) is None

    test_data = [
        (
            0,
            [
                {'id': 2, "name": "test2", 'alg_id': 3},
                {'id': 3, "name": "test3", 'alg_id': 3},
                {'id': 4, "name": "test4", 'alg_id': 4},
            ],
            [
                {'id': 1, 'hashlist_id': 2, 'hash': 'a', 'salt': '', 'summ': '0cc175b9c0f1b6a831c399e269772661'},
                {'id': 2, 'hashlist_id': 3, 'hash': 'a', 'salt': '', 'summ': '0cc175b9c0f1b6a831c399e269772661'},
                {'id': 3, 'hashlist_id': 4, 'hash': 'a', 'salt': '', 'summ': '0cc175b9c0f1b6a831c399e269772661'},
            ],
            "a:70617373"
        ),
        (
            1,
            [
                {'id': 2, "name": "test2", 'alg_id': 3},
                {'id': 3, "name": "test3", 'alg_id': 3},
                {'id': 4, "name": "test4", 'alg_id': 4},
            ],
            [
                {'id': 1, 'hashlist_id': 2, 'hash': 'a', 'salt': 'b', 'summ': 'd8160c9b3dc20d4e931aeb4f45262155'},
                {'id': 2, 'hashlist_id': 3, 'hash': 'a', 'salt': 'b', 'summ': 'd8160c9b3dc20d4e931aeb4f45262155'},
                {'id': 3, 'hashlist_id': 4, 'hash': 'a', 'salt': 'b', 'summ': 'd8160c9b3dc20d4e931aeb4f45262155'},
            ],
            "a:b:70617373"
        ),
    ]
    @pytest.mark.parametrize("have_salt,hashlists,hashes,outfile_content", test_data)
    def test_parse_outfile_and_fill_found_hashes(self, have_salt, hashlists, hashes, outfile_content):
        """ Test of parse_outfile_and_fill_found_hashes() """
        for hashlist in hashlists:
            self._add_hashlist(id=hashlist['id'], name=hashlist['name'],
                               alg_id=hashlist['alg_id'], have_salts=have_salt)

        for _hash in hashes:
            self._add_hash(id=_hash['id'], hashlist_id=_hash['hashlist_id'],
                           hash=_hash['hash'], salt=_hash['salt'], summ=_hash['summ'])

        file_put_contents("/tmp/test.txt", outfile_content)

        assert [] == self.db.fetch_all("SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl "
                                       "WHERE hl.id = h.hashlist_id AND hl.alg_id = 3 AND LENGTH(h.password) "
                                       "AND h.cracked")

        self.thrd.parse_outfile_and_fill_found_hashes({'out_file': '/tmp/test.txt'}, {'alg_id': 3})

        test_data = [
            {'id': 1, 'password': 'pass', 'cracked': 1},
            {'id': 2, 'password': 'pass', 'cracked': 1}
        ]
        assert test_data == self.db.fetch_all(
            "SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl WHERE hl.id = h.hashlist_id "
            "AND hl.alg_id = 3 AND LENGTH(h.password) AND h.cracked")
        assert [{'id': 3, 'password': '', 'cracked': 0}] == self.db.fetch_all(
            "SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl WHERE hl.id = h.hashlist_id "
            "AND hl.alg_id = 4")

    def test_update_task_uncracked_count(self):
        """ Test of update_task_uncracked_count() """
        self.db.update("task_works", {"uncracked_after": 100}, "id=1")
        self._add_hash(password='p', hash='a', salt='b', cracked=1)
        self._add_hash(hash='c', salt='d', cracked=0)
        self.thrd.update_task_uncracked_count(1, 1)
        assert self.db.fetch_one("SELECT uncracked_after FROM task_works WHERE id=1") == 1
