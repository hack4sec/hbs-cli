# -*- coding: utf-8 -*-

import sys
import configparser
import os
import time
import pytest
from pprint import pprint

sys.path.append('../../')
sys.path.append('../')

from libs.common import _d, file_get_contents, file_put_contents, md5
from classes.Registry import Registry
from classes.Database import Database
from classes.ResultParseThread import ResultParseThread
from classes.HbsException import HbsException
from CommonUnit import CommonUnit

class Test_ResultParseThread(CommonUnit):

    thrd = None

    def setup(self):
        self._clean_db()
        self._add_work_task()
        self.thrd = ResultParseThread()
        self.thrd.current_work_task_id = 1

    def teardown(self):
        if isinstance(self.thrd, ResultParseThread):
            del self.thrd
        #self._clean_db()

    def test_update_status(self):
        self._add_work_task(id=2)
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=1") == 'wait'
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=2") == 'wait'
        self.thrd._update_status('done')
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=1") == 'done'
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=2") == 'wait'

    def test_get_work_task_data(self):
        data1 = self.thrd._get_work_task_data()
        test_data1 = {'id': 1, 'task_id': 1, 'hashlist_id': 1, 'status': 'wait'}
        for field in test_data1:
            assert data1[field] == test_data1[field]

        self._add_work_task(id=2, hashlist_id=3, task_id=4, status='outparsing')

        self.thrd.current_work_task_id = 1
        data2 = self.thrd._get_work_task_data()
        test_data2 = {'id': 2, 'task_id': 4, 'hashlist_id': 3, 'status': 'outparsing'}
        for field in test_data2:
            assert data2[field] == test_data1[field]

    def test_update_work_task_field(self):
        self.thrd._update_work_task_field('status', 'done')
        self.thrd._update_work_task_field('hashlist_id', '2')
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=1") == 'done'
        assert self.db.fetch_one("SELECT hashlist_id FROM task_works WHERE id=1") == 2

    def test_update_all_hashlists_counts(self):
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

        self.thrd._update_all_hashlists_counts_by_alg_id(3)

        assert 1 == self.db.fetch_one("SELECT uncracked FROM hashlists WHERE id=1")
        assert 1 == self.db.fetch_one("SELECT cracked FROM hashlists WHERE id=1")

        assert 2 == self.db.fetch_one("SELECT uncracked FROM hashlists WHERE id=2")
        assert 1 == self.db.fetch_one("SELECT cracked FROM hashlists WHERE id=2")

        assert 4 == self.db.fetch_one("SELECT uncracked FROM hashlists WHERE id=3")
        assert 2 == self.db.fetch_one("SELECT cracked FROM hashlists WHERE id=3")

    def test_get_current_work_task(self):
        assert self.thrd._get_current_work_task_id() == 1

        self.thrd.current_work_task_id = 2
        assert self.thrd._get_current_work_task_id() == 2

        with pytest.raises(HbsException) as ex:
            self.thrd.current_work_task_id = None
            self.thrd._get_current_work_task_id()
        assert "Current task for work not set" in str(ex)

    def test_get_waiting_task_for_work(self):
        self._add_work_task(id=2, status='waitoutparse')
        assert self.thrd._get_waiting_task_for_work() == 2
        assert self.thrd.current_work_task_id == 2

        self.db.update("task_works", {'status': 'waitoutparse'}, "id = 1")
        assert self.thrd._get_waiting_task_for_work() == 1
        assert self.thrd.current_work_task_id == 1

        self.db.q("UPDATE task_works SET status = 'wait'")
        with pytest.raises(HbsException) as ex:
            self.thrd._get_waiting_task_for_work()
        assert "Current task for work not set" in str(ex)
        assert self.thrd.current_work_task_id == None

    def test_get_hashlist_data(self):
        self._add_hashlist()
        assert self.db.fetch_row("SELECT * FROM hashlists WHERE id = 1") == self.thrd._get_hashlist_data(1)
        assert None == self.thrd._get_hashlist_data(33)

    def test_parse_outfile_and_fill_found_hashes_wo_salts(self):
        self._add_hashlist(id=2, name="test2", alg_id=3, have_salts=0)
        self._add_hashlist(id=3, name="test3", alg_id=3, have_salts=0)
        self._add_hash(id=1, hashlist_id=2, hash='a', salt='',summ='0cc175b9c0f1b6a831c399e269772661')
        self._add_hash(id=2, hashlist_id=3, hash='a', salt='', summ='0cc175b9c0f1b6a831c399e269772661')

        self._add_hashlist(id=4, name="test3", alg_id=4, have_salts=0) # Diff alg
        self._add_hash(id=3, hashlist_id=4, hash='a', salt='', summ='0cc175b9c0f1b6a831c399e269772661')

        file_put_contents("/tmp/test.txt", "a:70617373")

        assert [] == self.db.fetch_all("SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl WHERE hl.id = h.hashlist_id AND hl.alg_id = 3 AND LENGTH(h.password) AND h.cracked")

        self.thrd._parse_outfile_and_fill_found_hashes({'out_file': '/tmp/test.txt'}, {'alg_id': 3})

        test_data = [
            {'id': 1, 'password': 'pass', 'cracked': 1},
            {'id': 2, 'password': 'pass', 'cracked': 1}
        ]
        assert test_data == self.db.fetch_all("SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl WHERE hl.id = h.hashlist_id AND hl.alg_id = 3 AND LENGTH(h.password) AND h.cracked")
        assert [{'id': 3, 'password': '', 'cracked': 0}] == self.db.fetch_all("SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl WHERE hl.id = h.hashlist_id AND hl.alg_id = 4")

    def test_parse_outfile_and_fill_found_hashes_w_salts(self):
        self._add_hashlist(id=2, name="test2", alg_id=3, have_salts=1)
        self._add_hashlist(id=3, name="test3", alg_id=3, have_salts=1)
        self._add_hash(id=1, hashlist_id=2, hash='a', salt='b',summ='d8160c9b3dc20d4e931aeb4f45262155')
        self._add_hash(id=2, hashlist_id=3, hash='a', salt='b', summ='d8160c9b3dc20d4e931aeb4f45262155')

        self._add_hashlist(id=4, name="test3", alg_id=4, have_salts=1) # Diff alg
        self._add_hash(id=3, hashlist_id=4, hash='a', salt='b', summ='d8160c9b3dc20d4e931aeb4f45262155')

        file_put_contents("/tmp/test.txt", "a:b:70617373")

        assert [] == self.db.fetch_all("SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl WHERE hl.id = h.hashlist_id AND hl.alg_id = 3 AND LENGTH(h.password) AND h.cracked")

        self.thrd._parse_outfile_and_fill_found_hashes({'out_file': '/tmp/test.txt'}, {'alg_id': 3})

        test_data = [
            {'id': 1, 'password': 'pass', 'cracked': 1},
            {'id': 2, 'password': 'pass', 'cracked': 1}
        ]
        assert test_data == self.db.fetch_all("SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl WHERE hl.id = h.hashlist_id AND hl.alg_id = 3 AND LENGTH(h.password) AND h.cracked")
        assert [{'id': 3, 'password': '', 'cracked': 0}] == self.db.fetch_all("SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl WHERE hl.id = h.hashlist_id AND hl.alg_id = 4")

    def test_update_task_uncracked_count(self):
        self.db.update("task_works", {"uncracked_after": 100}, "id=1")
        self._add_hash(password='p', hash='a', salt='b', cracked=1)
        self._add_hash(hash='c', salt='d', cracked=0)
        self.thrd._update_task_uncracked_count(1, 1)
        assert self.db.fetch_one("SELECT uncracked_after FROM task_works WHERE id=1") == 1