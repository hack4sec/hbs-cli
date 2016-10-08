# -*- coding: utf-8 -*-

import sys
import configparser
import os
import time
import unittest
import pprint

sys.path.append('../')
# на формирование итогового хешлиста (в конце)
#TODO в основном кроне не брать задач с необработанных хешлистов
# После каждой выполненной задачи перегенеривать хешлист

from libs.common import _d, file_get_contents, file_put_contents, md5
from classes.Registry import Registry
from classes.Database import Database
from classes.HashlistsLoaderThread import HashlistsLoaderThread

config = configparser.ConfigParser()
config.read(os.getcwd() + '/../' + 'config.ini')
Registry().set('config', config)

db = Database(
    config['main']['mysql_host'],
    config['main']['mysql_user'],
    config['main']['mysql_pass'],
    config['main']['mysql_dbname'],
)
Registry().set('db', db)

class CommonTest(unittest.TestCase):
    thrd = None
    db = None
    
    def __init__(self, methodName='runTest'):
        unittest.TestCase.__init__(self, methodName)

        self.config = configparser.ConfigParser()
        self.config.read(os.getcwd() + '/' + 'config.ini')
        #self.db = Registry().get('db')

        self.maxDiff = None

    def _startThrd(self):
        self.thrd = HashlistsLoaderThread()
        self.thrd.daemon = True
        self.thrd.start()

    def _stopThrd(self):
        del self.thrd
        self.thrd = None

    def setUp(self):
        self.db = Database(
            config['main']['mysql_host'],
            config['main']['mysql_user'],
            config['main']['mysql_pass'],
            config['main']['mysql_dbname'],
        )

        self.db.q("TRUNCATE TABLE `hashlists`")
        self.db.q("TRUNCATE TABLE `hashes`")

    def tearDown(self):
        self.db.close()

    def _test(self, hashlist_content, hashes_check_data, have_salts=0):
        file_put_contents("/tmp/test.txt", hashlist_content)
        self._add_list(have_salts=have_salts)

        self._startThrd()
        while self.db.fetch_one("SELECT COUNT(id) FROM hashlists WHERE `parsed` = 0"):
            time.sleep(1)
        self._stopThrd()

        test_data = self.db.fetch_all("SELECT hash, salt, password, cracked FROM hashes ORDER BY id ASC")
        self.assertEqual(hashes_check_data, test_data)

    def _add_list(self, have_salts=0):
        self.db.insert(
            "hashlists",
            {
                "name": "test",
                "alg_id": "2",
                "have_salts": str(have_salts),
                "delimiter": ":",
                "parsed": "0",
                "tmp_path": "/tmp/test.txt"
            }
        )

    def test_load_simple_list_wo_salts(self):
        self._test(
            "aaaa\nbbbb\ncccc",
            [
                {u'hash': u'aaaa', u'salt': u'', u'password': u'', u'cracked': 0},
                {u'hash': u'bbbb', u'salt': u'', u'password': u'', u'cracked': 0},
                {u'hash': u'cccc', u'salt': u'', u'password': u'', u'cracked': 0},
            ]
        )
        self.assertEqual(
            self.db.fetch_all("SELECT name, cracked, uncracked FROM hashlists WHERE id = 1"),
            [
                {u'name': u'test', u'cracked': 0, u'uncracked': 3},
            ]
        )

    def test_find_similar(self):
        id = self.db.insert(
            "hashlists",
            {
                "name": "test_similar",
                "alg_id": "2",
                "have_salts": 0,
                "delimiter": ":",
                "parsed": "1",
            }
        )
        self.db.insert(
            "hashes",
            {
                'hashlist_id': id, 'hash': 'aaaa', 'salt': '', 'password': 'test', 'cracked': '1', 'summ': md5('aaaa')
            }
        )
        file_put_contents("/tmp/test.txt", "aaaa\nbbbb\ncccc")
        self._add_list(have_salts=0)

        self._startThrd()
        while self.db.fetch_one("SELECT COUNT(id) FROM hashlists WHERE `parsed` = 0"):
            time.sleep(1)
        self._stopThrd()

        self.assertEqual(self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='aaaa' AND cracked AND password='test'"), 2)
        self.assertEqual(self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='aaaa' AND !cracked"), 0)

        self.assertEqual(
            self.db.fetch_all("SELECT name, cracked, uncracked FROM hashlists WHERE id = 2"),
            [
                {u'name': u'test', u'cracked': 1, u'uncracked': 2},
            ]
        )

    def test_find_similar_w_salts(self):
        id = self.db.insert(
            "hashlists",
            {
                "name": "test_similar",
                "alg_id": "2",
                "have_salts": 1,
                "delimiter": ":",
                "parsed": "1",
            }
        )
        self.db.insert(
            "hashes",
            {
                'hashlist_id': id, 'hash': 'aaaa', 'salt': '123', 'password': 'test', 'cracked': '1', 'summ': md5('aaaa:123')
            }
        )
        file_put_contents("/tmp/test.txt", "aaaa:123\nbbbb:456\ncccc:789")
        self._add_list(have_salts=1)

        self._startThrd()
        while self.db.fetch_one("SELECT COUNT(id) FROM hashlists WHERE `parsed` = 0"):
            time.sleep(1)
        self._stopThrd()

        self.assertEqual(self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='aaaa' AND cracked AND password='test'"), 2)
        self.assertEqual(self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hash='aaaa' AND !cracked"), 0)

        self.assertEqual(
            self.db.fetch_all("SELECT name, cracked, uncracked FROM hashlists WHERE id = 2"),
            [
                {u'name': u'test', u'cracked': 1, u'uncracked': 2},
            ]
        )


    def test_load_simple_list_remove_tmp_files(self):
        tmp_dir = Registry().get('config')['main']['tmp_dir']
        files_before = os.listdir(tmp_dir)
        self._test(
            "aaaa\nbbbb\ncccc",
            [
                {u'hash': u'aaaa', u'salt': u'', u'password': u'', u'cracked': 0},
                {u'hash': u'bbbb', u'salt': u'', u'password': u'', u'cracked': 0},
                {u'hash': u'cccc', u'salt': u'', u'password': u'', u'cracked': 0},
            ]
        )
        files_after = os.listdir(tmp_dir)
        self.assertEqual(files_before, files_after)


    def test_load_simple_list_remove_dups(self):
        self._test(
            "aaaa\nbbbb\ncccc\naaaa",
            [
                {u'hash': u'aaaa', u'salt': u'', u'password': u'', u'cracked': 0},
                {u'hash': u'bbbb', u'salt': u'', u'password': u'', u'cracked': 0},
                {u'hash': u'cccc', u'salt': u'', u'password': u'', u'cracked': 0},
            ]
        )

    def test_load_simple_list_w_salts(self):
        self._test(
            "aaaa:111\nbbbb:222\ncccc:333",
            [
                {u'hash': u'aaaa', u'salt': u'111', u'password': u'', u'cracked': 0},
                {u'hash': u'bbbb', u'salt': u'222', u'password': u'', u'cracked': 0},
                {u'hash': u'cccc', u'salt': u'333', u'password': u'', u'cracked': 0},
            ],
            have_salts=1
        )

    def test_load_simple_list_w_salts_and_error_line(self):
        self._test(
            "aaaa:111\nbbbb:222\ncccc:333\ndddd",
            [
                {u'hash': u'aaaa', u'salt': u'111', u'password': u'', u'cracked': 0},
                {u'hash': u'bbbb', u'salt': u'222', u'password': u'', u'cracked': 0},
                {u'hash': u'cccc', u'salt': u'333', u'password': u'', u'cracked': 0},
            ],
            have_salts=1
        )
        self.assertEqual(self.db.fetch_one("SELECT errors FROM hashlists"), "dddd\n")

    def test_load_simple_list_w_quotes(self):
        self._test(
            "aaaa:1'11\nb'bb\"b:222\ncccc:3\\\\33",
            [
                {u'hash': u'aaaa', u'salt': u'1\'11', u'password': u'', u'cracked': 0},
                {u'hash': u'b\'bb"b', u'salt': u'222', u'password': u'', u'cracked': 0},
                {u'hash': u'cccc', u'salt': u'3\\33', u'password': u'', u'cracked': 0},
            ],
            have_salts=1
        )



if __name__ == "__main__":
    unittest.main()