# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Common class for integration tests
"""

import os

import configparser

from classes.Registry import Registry
from classes.Database import Database


class LoggerMock(object):
    """ Mock for logger class """
    def log(self, module, message):
        pass

class CommonIntegration(object):
    """ Common class for integration tests """
    db = None

    def setup_class(self):
        """ Prepare class for run tests """
        CURPATH = os.path.dirname(__file__) + "/"

        config = configparser.ConfigParser()
        config.read(CURPATH + 'config.ini')
        Registry().set('config', config)

        Registry().set('logger', LoggerMock())

        db = Database(
            config['main']['mysql_host'],
            config['main']['mysql_user'],
            config['main']['mysql_pass'],
            config['main']['mysql_dbname'],
        )
        Registry().set('db', db)

        self.db = Registry().get('db')  # type: Database

    def _clean_db(self):
        """ Clean tables for tests """
        self.db.q("TRUNCATE TABLE dicts")
        self.db.q("TRUNCATE TABLE dicts_groups")
        self.db.q("TRUNCATE TABLE hashes")
        self.db.q("TRUNCATE TABLE hashlists")
        self.db.q("TRUNCATE TABLE rules")
        self.db.q("TRUNCATE TABLE tasks")
        self.db.q("TRUNCATE TABLE tasks_groups")
        self.db.q("TRUNCATE TABLE task_works")
        self.db.q("TRUNCATE TABLE logs")

        self.db.update("algs", {'finder_insidepro_allowed': 0}, "id")

    def _add_hashlist(
            self, id=1, name='test', alg_id=3, have_salts=0, status='ready',
            common_by_alg=0, parsed=1, tmp_path='', last_finder_checked=0):
        """ Add hashlist record """
        self.db.insert(
            "hashlists",
            {
                'id': id,
                'name': name,
                'alg_id': alg_id,
                'have_salts': have_salts,
                'delimiter': 'UNIQUEDELIMITER' if have_salts else '',
                'cracked': 0,
                'uncracked': 0,
                'errors': '',
                'parsed': parsed,
                'tmp_path': tmp_path,
                'status': status,
                'when_loaded': 0,
                'common_by_alg': common_by_alg,
                'last_finder_checked': last_finder_checked,
            }
        )

    def _add_hash(self, hashlist_id=1, hash='', salt='', summ='', password='', cracked=0, id=None):
        """ Add hash record """
        self.db.insert(
            "hashes",
            {
                'id': id,
                'hashlist_id': hashlist_id,
                'hash': hash,
                'salt': salt,
                'password': password,
                'cracked': cracked,
                'summ': summ
            }
        )

    def _add_work_task(self, id=1, hashlist_id=1, task_id=1, status='wait', priority=0, out_file=''):
        """ Add work task record """
        self.db.insert(
            "task_works",
            {
                'id': id,
                'hashlist_id': hashlist_id,
                'task_id': task_id,
                'status': status,
                'priority': priority,
                'out_file': out_file,
            }
        )

    def _add_task(self, id=1, name='task', group_id=1, type='dict', source=1):
        """ Add task record """
        self.db.insert(
            "tasks",
            {
                'id': id,
                'name': name,
                'group_id': group_id,
                'type': type,
                'source': source,
            }
        )

    def _add_dict(self, id=1, group_id=1, name='dict', hash='1'):
        """ Add dict record """
        self.db.insert(
            "dicts",
            {
                'id': id,
                'name': name,
                'group_id': group_id,
                'hash': hash,
            }
        )

    def _add_dict_group(self, id=1, name='group'):
        """ Add dict group record """
        self.db.insert(
            "dicts_groups",
            {
                'id': id,
                'name': name,
            }
        )

    def _add_rule(self, id=1, name='rule', hash='1.rule', count=1):
        """ Add rule record """
        self.db.insert(
            "rules",
            {
                'id': id,
                'name': name,
                'hash': hash,
                'count': count
            }
        )
