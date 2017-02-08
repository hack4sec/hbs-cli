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
from classes.HashlistsLoaderThread import HashlistsLoaderThread
from classes.HbsException import HbsException


class Test_HashlistsLoaderThread(CommonUnit):
    thrd = None

    def setup(self):
        self._clean_db()
        self._add_hashlist()
        self.thrd = HashlistsLoaderThread()
        self.thrd._current_hashlist_id = 1

    def teardown(self):
        if isinstance(self.thrd, HashlistsLoaderThread):
            del self.thrd
        #self._clean_db()

    def test_update_status(self):
        self._add_hashlist(id=2, status='ready')
        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id=1") == 'ready'
        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id=2") == 'ready'
        self.thrd._update_status('wait')
        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id=1") == 'wait'
        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id=2") == 'ready'

    def test_parsed_flag(self):
        self._add_hashlist(id=2)
        assert self.db.fetch_one("SELECT parsed FROM hashlists WHERE id=1") == 1
        assert self.db.fetch_one("SELECT parsed FROM hashlists WHERE id=2") == 1
        self.thrd._parsed_flag(0)
        assert self.db.fetch_one("SELECT parsed FROM hashlists WHERE id=1") == 0
        assert self.db.fetch_one("SELECT parsed FROM hashlists WHERE id=2") == 1

    def test_sort_file(self):
        test_file = '/tmp/test.txt'
        if os.path.exists(test_file):
            os.remove(test_file)
        file_put_contents(test_file, 'a\nc\nb\nb\nc')

        sorted_file = self.thrd._sort_file({'tmp_path': test_file})

        assert file_get_contents(sorted_file) == 'a\nb\nc\n'

    def test_sorted_file_to_db_file_without_salts(self):
        test_file = '/tmp/test.txt'
        if os.path.exists(test_file):
            os.remove(test_file)
        file_put_contents(test_file, 'a\nb\nc')
        file_to_db = self.thrd._sorted_file_to_db_file(test_file, {'have_salts': 0, 'id': 1})

        test_data = '"1","a","","{0}"\n"1","b","","{1}"\n"1","c","","{2}"\n'.format(md5('a'), md5('b'), md5('c'))
        assert file_get_contents(file_to_db) == test_data
        assert "preparedb" == self.db.fetch_one("SELECT status FROM hashlists WHERE id = 1")

    def test_sorted_file_to_db_file_with_salts(self):
        test_file = '/tmp/test.txt'
        if os.path.exists(test_file):
            os.remove(test_file)
        file_put_contents(test_file, 'a:x\nb:y\nc:z')
        file_to_db = self.thrd._sorted_file_to_db_file(test_file, {'have_salts': 1, 'delimiter':':', 'id': 1})

        test_data = '"1","a","x","{0}"\n"1","b","y","{1}"\n"1","c","z","{2}"\n'.format(md5('a:x'), md5('b:y'), md5('c:z'))
        assert file_get_contents(file_to_db) == test_data
        assert "preparedb" == self.db.fetch_one("SELECT status FROM hashlists WHERE id = 1")

    def test_sorted_file_to_db_file_with_special_chars(self):
        test_file = '/tmp/test.txt'
        if os.path.exists(test_file):
            os.remove(test_file)
        file_put_contents(test_file, 'a:x\'x\nb:y"y\nc:z\\z')
        file_to_db = self.thrd._sorted_file_to_db_file(test_file, {'have_salts': 1, 'delimiter':':', 'id': 1})

        test_data = '"1","a","x\'x","{0}"\n' \
                    '"1","b","y\\"y","{1}"\n' \
                    '"1","c","z\\\\z","{2}"\n'\
            .format(md5('a:x\'x'), md5('b:y"y'), md5('c:z\\z'))

        assert file_get_contents(file_to_db) == test_data
        assert "preparedb" == self.db.fetch_one("SELECT status FROM hashlists WHERE id = 1")

    def test_load_file_in_db_special_chars(self):
        test_file = '/tmp/test.txt'
        if os.path.exists(test_file):
            os.remove(test_file)
        file_put_contents(
            test_file,
            '"1","a","x\\\\nx","{0}"\n'
            '"1","b","y\\"y","{1}"\n'
            '"1","c","z\\\\z","{2}"\n'.format(md5('a:x\'x'), md5('b:y"y'), md5('c:z\\z'))
        )
        file_put_contents('/tmp/test1.txt', '')

        self.thrd._load_file_in_db(test_file, {'tmp_path': '/tmp/test1.txt'})

        test_hashes = [{'id': 1, 'hash': 'a', 'salt': r'x\nx'}, {'id': 2, 'hash': 'b', 'salt': 'y"y'}, {'id': 3, 'hash': 'c', 'salt': 'z\\z'}]
        for test_hash in test_hashes:
            test_row = self.db.fetch_row("SELECT id, hash, salt FROM hashes WHERE id = {0}".format(test_hash['id']))
            assert test_hash['hash'] == test_row['hash']
            assert test_hash['salt'] == test_row['salt']
        assert 3 == self.db.fetch_one("SELECT COUNT(id) FROM hashes")

        assert not os.path.exists('/tmp/test1.txt')

    def test_load_file_in_db(self):
        test_file = '/tmp/test.txt'
        if os.path.exists(test_file):
            os.remove(test_file)
        file_put_contents(test_file, '"1","a","e","x"\n"1","b","f","y"\n"1","c","g","z"\n')
        file_put_contents('/tmp/test1.txt', '')

        self.thrd._load_file_in_db(test_file, {'tmp_path': '/tmp/test1.txt'})

        test_hashes = [{'id': 1, 'hash': 'a', 'salt': 'e'}, {'id': 2, 'hash': 'b', 'salt': 'f'}, {'id': 3, 'hash': 'c', 'salt': 'g'}]
        for test_hash in test_hashes:
            test_row = self.db.fetch_row("SELECT id, hash, salt FROM hashes WHERE id = {0}".format(test_hash['id']))
            assert test_hash['hash'] == test_row['hash']
            assert test_hash['salt'] == test_row['salt']
        assert 3 == self.db.fetch_one("SELECT COUNT(id) FROM hashes")

    def test_find_similar_found_hashes(self):
        self._add_hash(hashlist_id=1, hash='a', salt='e', summ='x')
        self._add_hashlist(id=2)
        self._add_hash(hashlist_id=2, hash='a', salt='e', summ='x', password='111', cracked=1)
        self.thrd._find_similar_found_hashes({'id': 3, 'alg_id': 3})
        assert '111' == self.db.fetch_one("SELECT password FROM hashes WHERE hashlist_id=2 AND cracked=1 AND hash='a'")

    def test_get_hashlist_for_load(self):
        self._add_hashlist(id=2, parsed=0, status='wait')
        assert 2 == self.thrd._get_hashlist_for_load()

    def test_get_current_hashlist_id(self):
        assert self.thrd.get_current_hashlist_id() == 1

        self.thrd._current_hashlist_id = 2
        assert self.thrd.get_current_hashlist_id() == 2

        with pytest.raises(HbsException) as ex:
            self.thrd._current_hashlist_id = None
            self.thrd.get_current_hashlist_id()
        assert "Current hashlist not set" in str(ex)
