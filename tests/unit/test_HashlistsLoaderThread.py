# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

HashlistsLoaderThread unit tests
"""

import sys
import os
import time

import pytest

sys.path.append('../../')

from CommonUnit import CommonUnit
from libs.common import file_get_contents, file_put_contents, md5
from classes.HashlistsLoaderThread import HashlistsLoaderThread
from classes.HbsException import HbsException


class Test_HashlistsLoaderThread(CommonUnit):
    """ HashlistsLoaderThread unit tests """
    thrd = None

    def setup(self):
        """ Setup tests """
        self._clean_db()
        self._add_hashlist()
        self.thrd = HashlistsLoaderThread()
        self.thrd.current_hashlist_id = 1

    def teardown(self):
        """ Teardown tests """
        if isinstance(self.thrd, HashlistsLoaderThread):
            self.thrd.available = False
            time.sleep(1)
            del self.thrd
        self._clean_db()

    def test_update_status(self):
        """ test for update_status() """
        self._add_hashlist(id=2, status='ready')
        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id=1") == 'ready'
        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id=2") == 'ready'
        self.thrd.update_status('wait')
        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id=1") == 'wait'
        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id=2") == 'ready'

    def test_parsed_flag(self):
        """ test for parsed_flag() """
        self._add_hashlist(id=2)
        assert self.db.fetch_one("SELECT parsed FROM hashlists WHERE id=1") == 1
        assert self.db.fetch_one("SELECT parsed FROM hashlists WHERE id=2") == 1
        self.thrd.parsed_flag(0)
        assert self.db.fetch_one("SELECT parsed FROM hashlists WHERE id=1") == 0
        assert self.db.fetch_one("SELECT parsed FROM hashlists WHERE id=2") == 1

    def test_sort_file(self):
        """ test for sort_file() """
        test_file = '/tmp/test.txt'
        if os.path.exists(test_file):
            os.remove(test_file)
        file_put_contents(test_file, 'a\nc\nb\nb\nc')

        sorted_file = self.thrd.sort_file({'tmp_path': test_file})

        assert file_get_contents(sorted_file) == 'a\nb\nc\n'

    test_data = [
        (
            0,
            'a\nb\nc',
            '"1","a","","{0}"\n"1","b","","{1}"\n"1","c","","{2}"\n'.format(md5('a'), md5('b'), md5('c')),
        ),
        (
            1,
            'a:x\nb:y\nc:z',
            '"1","a","x","{0}"\n"1","b","y","{1}"\n"1","c","z","{2}"\n'.format(md5('a:x'), md5('b:y'), md5('c:z')),
        ),
        (
            1,
            'a:x\'x\nb:y"y\nc:z\\z',
            '"1","a","x\'x","{0}"\n"1","b","y\\"y","{1}"\n"1","c","z\\\\z","{2}"\n'
            .format(md5('a:x\'x'), md5('b:y"y'), md5('c:z\\z'))
        ),
    ]
    @pytest.mark.parametrize("have_salt,content,expected_content", test_data)
    def test_sorted_file_to_db(self, have_salt, content, expected_content):
        """
        Test sorted_file_to_db()
        :param have_salt: does hashlist has salt
        :param content: hashlist content (txt)
        :param expected_content: expected hashlist content after convertation
        :return:
        """
        test_file = '/tmp/test.txt'
        if os.path.exists(test_file):
            os.remove(test_file)
        file_put_contents(test_file, content)
        file_to_db = self.thrd.sorted_file_to_db_file(test_file, {'have_salts': have_salt, 'id': 1, 'delimiter': ':'})

        assert file_get_contents(file_to_db) == expected_content
        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id = 1") == "preparedb"

    test_data = [
        (
            '"1","a","x\\\\nx","{0}"\n"1","b","y\\"y","{1}"\n"1","c","z\\\\z","{2}"\n'
            .format(md5('a:x\'x'), md5('b:y"y'), md5('c:z\\z')),
            [{'id': 1, 'hash': 'a', 'salt': r'x\nx'}, {'id': 2, 'hash': 'b', 'salt': 'y"y'},
             {'id': 3, 'hash': 'c', 'salt': 'z\\z'}]
        ),
        (
            '"1","a","e","x"\n"1","b","f","y"\n"1","c","g","z"\n',
            [{'id': 1, 'hash': 'a', 'salt': 'e'}, {'id': 2, 'hash': 'b', 'salt': 'f'},
             {'id': 3, 'hash': 'c', 'salt': 'g'}]
        )
    ]
    @pytest.mark.parametrize("content,expected_hashes", test_data)
    def test_load_file_in_db(self, content, expected_hashes):
        """
        Test load_file_in_db()
        :param content: text content for in-db load
        :param expected_hashes: expected rows from db
        :return:
        """
        test_file = '/tmp/test.txt'
        if os.path.exists(test_file):
            os.remove(test_file)
        file_put_contents(test_file, content)
        file_put_contents('/tmp/test1.txt', '')

        self.thrd.load_file_in_db(test_file)

        for test_hash in expected_hashes:
            test_row = self.db.fetch_row("SELECT id, hash, salt FROM hashes WHERE id = {0}".format(test_hash['id']))
            assert test_hash['hash'] == test_row['hash']
            assert test_hash['salt'] == test_row['salt']
        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes") == 3

        assert not os.path.exists('/tmp/test1.txt')

    def test_find_similar_found_hashes(self):
        """ Test  find_similar_found_hashes() """
        self._add_hash(hashlist_id=1, hash='a', salt='e', summ='x')
        self._add_hashlist(id=2)
        self._add_hash(hashlist_id=2, hash='a', salt='e', summ='x', password='111', cracked=1)
        self.thrd.find_similar_found_hashes({'id': 3, 'alg_id': 3})
        assert self.db.fetch_one("SELECT password FROM hashes WHERE hashlist_id=2 AND cracked=1 AND hash='a'") == '111'

    def test_get_hashlist_for_load(self):
        """ Test get_hashlist_for_load() """
        self._add_hashlist(id=2, parsed=0, status='wait')
        assert self.thrd.get_hashlist_for_load() == 2

    def test_get_current_hashlist_id(self):
        """ Test get_current_hashlist_id() """
        assert self.thrd.get_current_hashlist_id() == 1

        self.thrd.current_hashlist_id = 2
        assert self.thrd.get_current_hashlist_id() == 2

        with pytest.raises(HbsException) as ex:
            self.thrd.current_hashlist_id = None
            self.thrd.get_current_hashlist_id()
        assert "Current hashlist not set" in str(ex)
