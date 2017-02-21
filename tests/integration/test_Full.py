# -*- coding: utf-8 -*-

import sys
import time
import os
import pytest
import json
from subprocess import Popen, PIPE
import pprint, signal

sys.path.append('../../')

from libs.common import md5, file_put_contents, file_get_contents
from classes.WorkerThread import WorkerThread
from CommonIntegration import CommonIntegration
from classes.Registry import Registry


class Test_Full(CommonIntegration):
    thrd = None

    def setup(self):
        if not os.path.exists(Registry().get('config')['main']['path_to_hc']):
            pytest.fail("HC dir not exists")
        self._clean_db()

    def teardown(self):
        if isinstance(self.thrd, WorkerThread):
            del self.thrd
        self._clean_db()

    # Have one ready hashlist
    # Load new hashlist
    # Start brute on it
    # Found same hash in first hashlist
    def test_run_1(self):
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

        assert 'ready' == self.db.fetch_one("SELECT status FROM hashlists WHERE id=2")

        stdout = process.stdout.read()

        stderr = process.stderr.read().replace('Warning: Using a password on the command line interface can be insecure.\n', '')
        assert stderr == ''

        assert 9 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes")
        assert 2 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='ccc' AND hash = '{0}'".format(md5('ccc')))
        assert 2 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1")

        assert 'done' == self.db.fetch_one("SELECT status FROM task_works WHERE id=1")

        assert 1 == self.db.fetch_one("SELECT COUNT(id) FROM hashlists WHERE common_by_alg <> 0")
        assert 3 == self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hashlist_id = 3")

        assert 'All-MD5' == self.db.fetch_one("SELECT name FROM hashlists WHERE common_by_alg = 4")

    # Have one ready hashlist
    # Load new hashlist
    # Wait build common hashlist
    # Start brute on it
    # Found same hash in first hashlist
    # Rebuild common hashlist
    def test_run_2(self):
        self._add_hashlist(alg_id=4)
        self._add_hash(hash=md5('333'), summ=md5(md5('333')))
        self._add_hash(hash=md5('444'), summ=md5(md5('444')))
        self._add_hash(hash=md5('ccc'), summ=md5(md5('ccc')))

        self._add_hashlist(id=2, parsed=0, tmp_path='/tmp/1.txt', status='wait', alg_id=4)
        file_put_contents('/tmp/1.txt', '{0}\n{1}\n{2}\n'.format(md5('111'), md5('333'), md5('ccc')))

        process = Popen("python ../../hbs.py", stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True, preexec_fn=os.setsid)
        time.sleep(10)

        assert 'All-MD5' == self.db.fetch_one("SELECT name FROM hashlists WHERE common_by_alg = 4")
        assert 3 == self.db.fetch_one("SELECT id FROM hashlists WHERE common_by_alg = 4")

        self._add_work_task(hashlist_id=3)
        self._add_task(source='?l?l?l', type='mask')

        time.sleep(20)

        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        stdout = process.stdout.read()

        stderr = process.stderr.read().replace('Warning: Using a password on the command line interface can be insecure.\n', '')
        assert stderr == ''

        assert 9 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes")
        assert 2 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='ccc' AND hash = '{0}'".format(md5('ccc')))
        assert 2 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1")

        assert 'done' == self.db.fetch_one("SELECT status FROM task_works WHERE id=1")

        assert 3 == self.db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hashlist_id = 3")

    # Priority change
    def test_run_3(self):
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

        while "work" != self.db.fetch_one("SELECT status FROM task_works WHERE id = 1"):
            pass

        self._add_work_task(id=2, hashlist_id=1, priority=100)

        while "work" != self.db.fetch_one("SELECT status FROM task_works WHERE id = 2"):
            pass

        assert "wait" == self.db.fetch_one("SELECT status FROM task_works WHERE id = 1")

        time.sleep(30)

        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        stdout = process.stdout.read()

        stderr = process.stderr.read().replace('Warning: Using a password on the command line interface can be insecure.\n', '')
        assert stderr == ''
        #pprint.pprint(stdout)
        #assert False
        assert 1 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='ccccccc'")

        assert 1 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='zzzweeg'")

        assert 'done' == self.db.fetch_one("SELECT DISTINCT status FROM task_works")

        assert 'All-MD5' == self.db.fetch_one("SELECT name FROM hashlists WHERE common_by_alg = 4")
        assert 'All-md5(md5($pass))' == self.db.fetch_one("SELECT name FROM hashlists WHERE common_by_alg = 23")
        assert [3, 4] == self.db.fetch_col("SELECT id FROM hashlists WHERE common_by_alg")

    # Task working, stop, go next for end, first go again
    def test_run_4(self):
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
        while "work" != self.db.fetch_one("SELECT status FROM task_works WHERE id = 1"):
            if int(time.time()) - start_time > 5:
                pytest.fail("Timeout start first task")

        self._add_work_task(id=2, hashlist_id=1)
        self.db.update("task_works", {'status': 'go_stop'}, "id = 1")

        start_time = int(time.time())
        while "work" != self.db.fetch_one("SELECT status FROM task_works WHERE id = 2"):
            if int(time.time()) - start_time > 20:
                pytest.fail("Timeout start second task")

        self.db.update("task_works", {'status': 'wait'}, "id = 1")

        start_time = int(time.time())
        while "work" != self.db.fetch_one("SELECT status FROM task_works WHERE id = 1"):
            file_put_contents(
                '/tmp/time.txt',
                "{0}{1}\n".format(
                    time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                    self.db.fetch_one("SELECT status FROM task_works WHERE id = 1")
                ),
                True)
            if int(time.time()) - start_time > 40:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                pprint.pprint(process.stdout.read())
                pytest.fail("Timeout start first task after stop")
            time.sleep(1)

        assert "done" == self.db.fetch_one("SELECT status FROM task_works WHERE id = 2");

        time.sleep(30)

        assert "done" == self.db.fetch_one("SELECT status FROM task_works WHERE id = 1");

        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

        stdout = process.stdout.read()

        stderr = process.stderr.read().replace('Warning: Using a password on the command line interface can be insecure.\n', '')
        assert stderr == ''

        assert 1 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='ccccccc'")

        assert 1 == self.db.fetch_one(
            "SELECT COUNT(id) FROM hashes WHERE cracked=1 AND password='zzzweeg'")

        assert 'done' == self.db.fetch_one("SELECT DISTINCT status FROM task_works")