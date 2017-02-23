# -*- coding: utf-8 -*-

import sys
import configparser
import os
import time
import pytest
from pprint import pprint

sys.path.append('../../')

from CommonUnit import CommonUnit
from libs.common import _d, file_get_contents, file_put_contents, md5
from classes.FinderInsideProThread import FinderInsideProThread
from classes.HbsException import HbsException


class Test_FinderInsideProThread(CommonUnit):
    thrd = None

    def setup(self):
        self._clean_db()
        self.thrd = FinderInsideProThread()

    def teardown(self):
        if isinstance(self.thrd, FinderInsideProThread):
            self.thrd.available = False
            time.sleep(1)
            del self.thrd
        self._clean_db()

    def test_is_alg_in_parse(self):
        assert False == self.thrd._is_alg_in_parse(3)
        self._add_hashlist(common_by_alg=1)
        self.db.insert("task_works", {'hashlist_id': 1, 'status': 'waitoutparse', 'task_id': 1})
        assert True == self.thrd._is_alg_in_parse(3)

        assert False == self.thrd._is_alg_in_parse(4)
        self._add_hashlist(id=2, alg_id=4, common_by_alg=1)
        self.db.insert("task_works", {'hashlist_id': 2, 'status': 'outparsing', 'task_id': 1})
        assert True == self.thrd._is_alg_in_parse(4)

    def test_get_ready_common_hashlists(self):
        self.db.update("algs", {'finder_insidepro_allowed': 1}, "id IN(3,4) ")
        self._add_hashlist(common_by_alg=3)
        self._add_hashlist(id=2, common_by_alg=4, last_finder_checked=int(time.time()))

        data = self.thrd._get_ready_common_hashlists()
        assert len(data) == 1
        assert data[0]['id'] == 1

        self.db.update("algs", {'finder_insidepro_allowed': 0}, "id IN(3) ")

        data = self.thrd._get_ready_common_hashlists()
        assert len(data) == 0

    def test_make_hashlist(self):
        self._add_hash(hash='a')
        self._add_hash(hash='b')
        self._add_hash(hash='c')

        self._add_hashlist(id=2, have_salts=1)
        self._add_hash(hashlist_id=2, hash='a', salt='1')
        self._add_hash(hashlist_id=2, hash='b', salt='2')
        self._add_hash(hashlist_id=2, hash='c', salt='3')

        file_path = self.thrd._make_hashlist(1)

        assert os.path.exists(file_path)
        assert "a\nb\nc\n" == file_get_contents(file_path)

        file_path = self.thrd._make_hashlist(2)

        assert os.path.exists(file_path)
        assert "a{0}1\nb{0}2\nc{0}3\n".format(FinderInsideProThread.UNIQUE_DELIMITER) == file_get_contents(file_path)

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
            [
                {'hash': 'a', 'salt': '', 'password': 'pass'},
            ]
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
            [
                {'hash': 'a', 'salt': 'b', 'password': 'pass'},
            ]
        ),
    ]
    @pytest.mark.parametrize("have_salt,hashlists,hashes,found_hashes", test_data)
    def test_put_found_hashes_in_db(self, have_salt, hashlists, hashes, found_hashes):
        for hashlist in hashlists:
            self._add_hashlist(id=hashlist['id'], name=hashlist['name'], alg_id=hashlist['alg_id'], have_salts=have_salt)

        for _hash in hashes:
            self._add_hash(id=_hash['id'], hashlist_id=_hash['hashlist_id'],
                           hash=_hash['hash'], salt=_hash['salt'], summ=_hash['summ'])

        assert [] == self.db.fetch_all(
            "SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl "
            "WHERE hl.id = h.hashlist_id AND hl.alg_id = 3 AND LENGTH(h.password) AND h.cracked"
        )

        self.thrd._put_found_hashes_in_db(3, found_hashes)

        test_data = [
            {'id': 1, 'password': 'pass', 'cracked': 1},
            {'id': 2, 'password': 'pass', 'cracked': 1}
        ]
        assert test_data == self.db.fetch_all(
            "SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl "
            "WHERE hl.id = h.hashlist_id AND hl.alg_id = 3 AND LENGTH(h.password) AND h.cracked")
        assert [{'id': 3, 'password': '', 'cracked': 0}] == self.db.fetch_all(
            "SELECT h.id, h.password, h.cracked FROM hashes h, hashlists hl "
            "WHERE hl.id = h.hashlist_id AND hl.alg_id = 4")