# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Class of integration tests - Full run
"""

import sys
import time
import os
import signal
from subprocess import Popen, PIPE

import pytest

sys.path.append('../../')

from libs.common import md5, file_put_contents
from classes.WorkerThread import WorkerThread
from CommonIntegration import CommonIntegration
from classes.Registry import Registry


class Test_Full(CommonIntegration):
    """ Class for integration tests - Full run """
    thrd = None

    def setup(self):
        """ Tests setup """
        if not os.path.exists(Registry().get('config')['main']['path_to_hc']):
            pytest.fail("HC dir not exists")
        self._clean_db()
        self.db.update("algs", {'finder_insidepro_allowed': 0}, "id")

    def teardown(self):
        """ Tests teardown """
        if isinstance(self.thrd, WorkerThread):
            del self.thrd
        self._clean_db()

    def test_run_1(self):
        """ Have one ready hashlist. Load new hashlist, start brute on it. Found same hashes in first hashlist """
        self._add_hashlist(alg_id=4)
        self._add_hash(hash=md5('333'), summ=md5(md5('333')))
        self._add_hash(hash=md5('444'), summ=md5(md5('444')))
        self._add_hash(hash=md5('ccc'), summ=md5(md5('ccc')))

        self._add_hashlist(id=2, parsed=0, tmp_path='/tmp/1.txt', status='wait', alg_id=4)
        file_put_contents('/tmp/1.txt', '{0}\n{1}\n{2}\n'.format(md5('111'), md5('333'), md5('ccc')))

        self._add_work_task(hashlist_id=2)
        self._add_task(source='?l?l?l', type='mask')

        process = Popen("python ../../hbs.py", stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True, preexec_fn=os.setsid)
        time.sleep(20)
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        assert self.db.fetch_one("SELECT status FROM hashlists WHERE id=2") == 'ready'

        #stdout = process.stdout.read()

        stderr = process.stderr.read()\
            .replace('Warning: Using a password on the command line interface can be insecure.\n', '')
        assert stderr == ''

        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes") == 9
        assert self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='ccc' AND hash = '{0}'".format(md5('ccc'))
        ) == 2
        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE cracked=1") == 2

        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=1") == 'done'

        assert self.db.fetch_one("SELECT COUNT(id) FROM hashlists WHERE common_by_alg <> 0") == 1
        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hashlist_id = 3") == 3

        assert self.db.fetch_one("SELECT name FROM hashlists WHERE common_by_alg = 4") == 'All-MD5'

    def test_run_2(self):
        """
        Have one ready hashlist. Load new hashlist. Wait common hashlist build.
        Start brute on it. Found one hash which exists in first & second hashlists.
        Rebuild common hashlist
        """
        self._add_hashlist(alg_id=4)
        self._add_hash(hash=md5('333'), summ=md5(md5('333')))
        self._add_hash(hash=md5('444'), summ=md5(md5('444')))
        self._add_hash(hash=md5('ccc'), summ=md5(md5('ccc')))

        self._add_hashlist(id=2, parsed=0, tmp_path='/tmp/1.txt', status='wait', alg_id=4)
        file_put_contents('/tmp/1.txt', '{0}\n{1}\n{2}\n'.format(md5('111'), md5('333'), md5('ccc')))

        process = Popen("python ../../hbs.py", stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True, preexec_fn=os.setsid)
        time.sleep(10)

        assert self.db.fetch_one("SELECT name FROM hashlists WHERE common_by_alg = 4") == 'All-MD5'
        assert self.db.fetch_one("SELECT id FROM hashlists WHERE common_by_alg = 4") == 3

        self._add_work_task(hashlist_id=3)
        self._add_task(source='?l?l?l', type='mask')

        time.sleep(20)

        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        #stdout = process.stdout.read()

        stderr = process.stderr.read()\
            .replace('Warning: Using a password on the command line interface can be insecure.\n', '')
        assert stderr == ''

        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes") == 9
        assert self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='ccc' AND hash = '{0}'".format(md5('ccc'))
        ) == 2
        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE cracked=1") == 2

        assert self.db.fetch_one("SELECT status FROM task_works WHERE id=1") == "done"

        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hashlist_id = 3") == 3

    def test_run_3(self):
        """
        Have 2 hashlists. Start task by one, add second with high priority. First task stop, start second.
        Wait for second done, and first return to work and done.
        """
        self._add_hashlist(alg_id=4)
        self._add_hash(hash=md5('333'), summ=md5(md5('333')))
        self._add_hash(hash=md5('444'), summ=md5(md5('444')))
        self._add_hash(hash=md5('ccccccc'), summ=md5(md5('ccc')))

        self._add_hashlist(id=2, alg_id=23)
        self._add_hash(hashlist_id=2, hash=md5(md5('333')), summ=md5(md5(md5('333'))))
        self._add_hash(hashlist_id=2, hash=md5(md5('444')), summ=md5(md5(md5('444'))))
        self._add_hash(hashlist_id=2, hash=md5(md5('zzzweeg')), summ=md5(md5(md5('ccc'))))

        process = Popen("python ../../hbs.py", stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True, preexec_fn=os.setsid)

        self._add_work_task(hashlist_id=2)
        self._add_task(source='?l?l?l?l?l?l?l', type='mask')

        start_time = int(time.time())
        while self.db.fetch_one("SELECT status FROM task_works WHERE id = 1") != "work":
            if int(time.time()) - start_time > 20:
                pytest.fail("Timeout start first task")

        self._add_work_task(id=2, hashlist_id=1, priority=100)

        start_time = int(time.time())
        while self.db.fetch_one("SELECT status FROM task_works WHERE id = 2") != "work":
            if int(time.time()) - start_time > 20:
                pytest.fail("Timeout start second task")

        assert self.db.fetch_one("SELECT status FROM task_works WHERE id = 1") == "wait"

        time.sleep(30)

        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        #stdout = process.stdout.read()

        stderr = process.stderr.read()\
            .replace('Warning: Using a password on the command line interface can be insecure.\n', '')
        assert stderr == ''

        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='ccccccc'") == 1

        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='zzzweeg'") == 1

        assert self.db.fetch_one("SELECT DISTINCT status FROM task_works") == 'done'

        assert self.db.fetch_one("SELECT name FROM hashlists WHERE common_by_alg = 4") == 'All-MD5'
        assert self.db.fetch_one("SELECT name FROM hashlists WHERE common_by_alg = 23") == 'All-md5(md5($pass))'
        assert self.db.fetch_col("SELECT id FROM hashlists WHERE common_by_alg") == [3, 4]

    def test_run_4(self):
        """
        Have 2 hashlists. Start one task by first, add second task with same priority. Stop first "manually", second
        start and done. After that first "manually" return to work.
        """
        self._add_hashlist(alg_id=4)
        self._add_hash(hash=md5('333'), summ=md5(md5('333')))
        self._add_hash(hash=md5('444'), summ=md5(md5('444')))
        self._add_hash(hash=md5('ccccccc'), summ=md5(md5('ccccccc')))

        self._add_hashlist(id=2, alg_id=23)
        self._add_hash(hashlist_id=2, hash=md5(md5('333')), summ=md5(md5(md5('333'))))
        self._add_hash(hashlist_id=2, hash=md5(md5('444')), summ=md5(md5(md5('444'))))
        self._add_hash(hashlist_id=2, hash=md5(md5('zzzweeg')), summ=md5(md5(md5('zzzweeg'))))

        self._add_hashlist(id=3, alg_id=4, common_by_alg=4)
        self._add_hash(hashlist_id=3, hash=md5('333'), summ=md5(md5('333')))
        self._add_hash(hashlist_id=3, hash=md5('444'), summ=md5(md5('444')))
        self._add_hash(hashlist_id=3, hash=md5('ccccccc'), summ=md5(md5('ccccccc')))

        self._add_hashlist(id=4, alg_id=23, common_by_alg=23)
        self._add_hash(hashlist_id=4, hash=md5(md5('333')), summ=md5(md5(md5('333'))))
        self._add_hash(hashlist_id=4, hash=md5(md5('444')), summ=md5(md5(md5('444'))))
        self._add_hash(hashlist_id=4, hash=md5(md5('zzzweeg')), summ=md5(md5(md5('zzzweeg'))))

        process = Popen("python ../../hbs.py", stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True, preexec_fn=os.setsid)

        self._add_work_task(hashlist_id=2)
        self._add_task(source='?l?l?l?l?l?l?l', type='mask')

        start_time = int(time.time())
        while self.db.fetch_one("SELECT status FROM task_works WHERE id = 1") != "work":
            if int(time.time()) - start_time > 5:
                pytest.fail("Timeout start first task")

        self._add_work_task(id=2, hashlist_id=1)
        self.db.update("task_works", {'status': 'go_stop'}, "id = 1")

        start_time = int(time.time())
        while self.db.fetch_one("SELECT status FROM task_works WHERE id = 2") != "work":
            if int(time.time()) - start_time > 20:
                pytest.fail("Timeout start second task")

        self.db.update("task_works", {'status': 'wait'}, "id = 1")

        start_time = int(time.time())
        while self.db.fetch_one("SELECT status FROM task_works WHERE id = 1") != "work":
            file_put_contents(
                '/tmp/time.txt',
                "{0}{1}\n".format(
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    self.db.fetch_one("SELECT status FROM task_works WHERE id = 1")
                ),
                True)
            if int(time.time()) - start_time > 40:
                pytest.fail("Timeout start first task after stop")
            time.sleep(1)

        assert self.db.fetch_one("SELECT status FROM task_works WHERE id = 2") == "done"

        time.sleep(30)

        assert self.db.fetch_one("SELECT status FROM task_works WHERE id = 1") == "done"

        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        #stdout = process.stdout.read()

        stderr = process.stderr.read()\
            .replace('Warning: Using a password on the command line interface can be insecure.\n', '')
        assert stderr == ''

        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='ccccccc'") == 1
        assert self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='zzzweeg'") == 1

        assert self.db.fetch_one("SELECT DISTINCT status FROM task_works") == "done"

    test_data = [
        (
            74,
            1,
            [
                {'id': 1, 'common_id': 2, 'hash': '0065ffe5f9e4e5996c2c3f52f81c6e31', 'salt': 'cB6Ar', 'cracked': 1,
                 'summ': md5("0065ffe5f9e4e5996c2c3f52f81c6e31:cB6Ar"), 'password': 'y0007171'},
                {'id': 3, 'common_id': 4, 'hash': '20e153b046072c949562f3c939611db8', 'salt': '0RTV', 'cracked': 0,
                 'summ': md5("20e153b046072c949562f3c939611db8:0RTV"), 'password': ''},
            ]
        ),
        (
            4,
            0,
            [
                {'id': 1, 'common_id': 2, 'hash': md5('aaa'), 'salt': '', 'cracked': 1,
                 'summ': md5(md5('aaa')), 'password': 'aaa'},
                {'id': 3, 'common_id': 4, 'hash': '10e153b046072c949562f3c939611db7', 'salt': '', 'cracked': 0,
                 'summ': md5("10e153b046072c949562f3c939611db7"), 'password': ''},
            ]
        )
    ]
    @pytest.mark.parametrize("alg_id,have_salt,hashes", test_data)
    def test_run_5(self, alg_id, have_salt, hashes):
        """
        Have no tasks, bun FinderInsidePro works
        :param alg_id:
        :param have_salt: Does alg has salt?
        :param hashes: Hashes rows
        :return:
        """
        self.db.update("algs", {'finder_insidepro_allowed': 1}, "id")

        self._add_hashlist(alg_id=alg_id, have_salts=have_salt)
        self._add_hashlist(id=2, alg_id=alg_id, have_salts=have_salt, common_by_alg=alg_id)
        for _hash in hashes:
            self._add_hash(hashlist_id=1, id=_hash['id'], hash=_hash['hash'], salt=_hash['salt'], summ=_hash['summ'])
            self._add_hash(hashlist_id=2, id=_hash['common_id'], hash=_hash['hash'],
                           salt=_hash['salt'], summ=_hash['summ'])

        process = Popen("python ../../hbs.py", stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True, preexec_fn=os.setsid)
        time.sleep(15)
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        print process.stdout.read()

        for _hash in hashes:
            test_data = self.db.fetch_row("SELECT * FROM hashes WHERE id = {0}".format(_hash['id']))
            assert test_data['summ'] == _hash['summ']
            assert test_data['cracked'] == _hash['cracked']
            assert test_data['password'] == _hash['password']
            # Was found and deleted by HashlistsByAlgThread
            assert self.db.fetch_row("SELECT * FROM hashes WHERE id = {0}".format(_hash['common_id'])) is None
