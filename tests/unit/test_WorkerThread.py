# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Unit tests for WorkerThread
"""
import sys
import os
import shutil
import json
import time

import pytest

sys.path.append('../../')

from libs.common import file_get_contents, file_put_contents
from classes.Registry import Registry
from classes.WorkerThread import WorkerThread
from classes.HbsException import HbsException
from CommonUnit import CommonUnit

class Test_WorkerThread(CommonUnit):
    """ Unit tests for WorkerThread """
    db = None # type: Database
    thrd = None

    def setup(self):
        """ tests setup """
        self._clean_db()
        self._add_hashlist()
        self._add_work_task()
        self.thrd = WorkerThread(self.db.fetch_row("SELECT * FROM task_works WHERE id = 1"))
        self.thrd.catch_exceptions = False

    def teardown(self):
        """ tests teardown """
        if isinstance(self.thrd, WorkerThread):
            self.thrd.available = False
            time.sleep(1)
            del self.thrd
        self._clean_db()

    def test_clean_stdout_file(self):
        """ Test of method which clean stdout file from automate-status entries """
        test_file = '/tmp/test.txt'

        if os.path.exists(test_file):
            os.remove(test_file)

        self.thrd.work_task = {'path_stdout': '/tmp/test.txt'}
        self.thrd.clean_stdout_file()
        assert file_get_contents(test_file) == ""

        file_put_contents(test_file, "some\nSTATUS ...\ntest\n\n\ntest2\r\n")
        self.thrd.clean_stdout_file()
        assert file_get_contents(test_file) == "some\ntest\ntest2\n"

    def test_refresh_work_task(self):
        """ Test of method task data update from db """
        self.db.update("task_works", {'status': 'done'}, "id = 1")
        assert self.thrd.work_task['status'] == "wait"
        self.thrd.refresh_work_task()
        assert self.thrd.work_task['status'] == "done"

    def test_not_high_priority(self):
        """ Test for get most priority work task """
        self._add_hashlist(id=2, alg_id=4)

        self._add_work_task(id=2, priority=1, hashlist_id=1)
        assert self.thrd.not_high_priority() == 2

        self.db.update("task_works", {'hashlist_id': 2, 'status': 'waitoutparse'}, "id = 2")
        assert self.thrd.not_high_priority() is None

        self.db.update("task_works", {'hashlist_id': 2, 'status': 'outparsing'}, "id = 2")
        assert self.thrd.not_high_priority() is None

        self.db.update("task_works", {'hashlist_id': 2, 'status': 'wait'}, "id = 2")
        assert self.thrd.not_high_priority() == 2

    def test_update_hc_status(self):
        """ Test of database update current hc-status (speed, t, etc) """
        test_data = self.db.fetch_row(
            "SELECT hc_status, hc_speed, hc_curku, hc_progress, hc_rechash, hc_temp "
            "FROM task_works WHERE id = 1"
        )
        for field in test_data:
            assert test_data[field] == ""
        self.thrd.update_hc_status(['status', 'speed', 'curku', 'progress', 'rechash', 'recsalt', 'temp'])
        test_data = self.db.fetch_row(
            "SELECT hc_status, hc_speed, hc_curku, hc_progress, hc_rechash, hc_temp "
            "FROM task_works WHERE id = 1"
        )
        assert test_data["hc_status"] == "status"
        assert test_data["hc_speed"] == "speed"
        assert test_data["hc_curku"] == "curku"
        assert test_data["hc_progress"] == "progress"
        assert test_data["hc_rechash"] == "rechash"
        assert test_data["hc_temp"] == "temp"

    def test_update_task_props(self):
        """ Test of method which update task properties """
        self._add_work_task(id=2)
        assert self.db.fetch_row("SELECT status, hc_temp FROM task_works WHERE id = 1") == \
               {"status": "wait", "hc_temp": ""}
        assert self.db.fetch_row("SELECT status, hc_temp FROM task_works WHERE id = 2") == \
               {"status": "wait", "hc_temp": ""}

        test_data = {'status': 'done', 'hc_temp': '1'}
        self.thrd.update_task_props(test_data)
        assert test_data == self.db.fetch_row("SELECT status, hc_temp FROM task_works WHERE id = 1")

        for field in test_data:
            assert test_data[field] == self.thrd.work_task[field]

        assert self.db.fetch_row("SELECT status, hc_temp FROM task_works WHERE id = 2") == \
               {"status": "wait", "hc_temp": ""}

    def test_make_hashlist(self):
        """ Test of hashlist building from db """
        self._add_hash(hash='a')
        self._add_hash(hash='b')
        self._add_hash(hash='c')

        self._add_hashlist(id=2, have_salts=1)
        self._add_hash(hashlist_id=2, hash='a', salt='1')
        self._add_hash(hashlist_id=2, hash='b', salt='2')
        self._add_hash(hashlist_id=2, hash='c', salt='3')

        file_path = self.thrd.make_hashlist()

        assert os.path.exists(file_path)
        assert file_get_contents(file_path) == "a\nb\nc\n"

        self.thrd.work_task['hashlist_id'] = 2
        file_path = self.thrd.make_hashlist()

        assert os.path.exists(file_path)
        assert file_get_contents(file_path) == "a:1\nb:2\nc:3\n"

    def test_calc_hashes_before(self):
        """ Test of calculating ancracked hashes count before task start """
        self._add_hash(hash='a')
        self._add_hash(hash='b')
        self._add_hash(hash='c')

        assert self.db.fetch_one("SELECT uncracked_before FROM task_works WHERE id = 1") == 0

        self.thrd.calc_hashes_before()

        assert self.db.fetch_one("SELECT uncracked_before FROM task_works WHERE id = 1") == 3

    def test_change_task_status(self):
        """ Test of update task status method """
        self._add_work_task(id=2, status='work')

        self.db.update("task_works", {'status': 'work'}, "id = 1")
        self.thrd.change_task_status(1, 0)

        assert self.db.fetch_one("SELECT status FROM task_works WHERE id = 1") == "wait"
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id = 2") == "work"

        self.db.update("task_works", {'status': 'work'}, "id = 1")
        self.thrd.change_task_status(0, 0)
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id = 1") == "waitoutparse"

        self.thrd.change_task_status(0, 1)
        assert self.db.fetch_one("SELECT status FROM task_works WHERE id = 1") == "stop"

    def test_get_task_data_by_id(self):
        """ Test of method which return task data by id  """
        self._add_task()
        test_data = {'id': 1, 'name': 'task', 'group_id': 1, 'type': 'dict'}
        task_data = self.thrd.get_task_data_by_id(1)
        for field in test_data:
            assert test_data[field] == task_data[field]

    def test_add_custom_charsets_to_cmd(self):
        """ Adding custom charsets to command """
        test_data1 = {'custom_charset1': '', 'custom_charset2': '', 'custom_charset3': '', 'custom_charset4': '', }
        test_data2 = {'custom_charset1': '1', 'custom_charset2': '', 'custom_charset3': '', 'custom_charset4': '', }
        test_data3 = {'custom_charset1': '1', 'custom_charset2': '2', 'custom_charset3': '3', 'custom_charset4': '4', }

        assert self.thrd.add_custom_charsets_to_cmd(test_data1, []) == []
        assert self.thrd.add_custom_charsets_to_cmd(test_data2, []) == ['--custom-charset1=1']
        assert self.thrd.add_custom_charsets_to_cmd(test_data3, []) == \
               ['--custom-charset1=1', '--custom-charset2=2', '--custom-charset3=3', '--custom-charset4=4']

    def test_add_increment_to_cmd(self):
        """ Adding increment to command """
        test_data1 = {'increment': 1, 'increment_min': 1, 'increment_max': 2}
        test_data2 = {'increment': 0, 'increment_min': 1, 'increment_max': 2}
        assert self.thrd.add_increment_to_cmd(test_data1, []) == \
               ['--increment', '--increment-min=1', '--increment-max=2']
        assert self.thrd.add_increment_to_cmd(test_data2, []) == []

        test_data3 = {'increment': 1, 'increment_min': 2, 'increment_max': 1}
        with pytest.raises(HbsException) as ex:
            self.thrd.add_increment_to_cmd(test_data3, [])
        assert "Wrong increment - from 2 to 1" in str(ex)

    def test_build_dicts(self):
        """ Test of symlinks on dicts build mechanism, for simple dicts attacks """
        tmp_dir = Registry().get('config')['main']['tmp_dir']
        dicts_path = Registry().get('config')['main']['dicts_path']

        if os.path.exists(tmp_dir + '/dicts_for_1'):
            shutil.rmtree(tmp_dir + '/dicts_for_1')

        os.mkdir(tmp_dir + '/dicts_for_1')
        assert tmp_dir + '/dicts_for_1' == self.thrd.build_dicts(0, {})

        shutil.rmtree(tmp_dir + '/dicts_for_1')

        self._add_dict()
        self._add_dict(id=2, hash='2')
        file_put_contents(dicts_path + "/1.dict", "aaa\nbbb")
        file_put_contents(dicts_path + "/2.dict", "ccc\nddd")

        self._add_dict(id=3, hash='3', group_id=2)
        file_put_contents(dicts_path + "/1.dict", "aaa\nbbb")

        path_to_dict = self.thrd.build_dicts(1, {'type': 'dict', 'source': 1})

        assert not os.path.exists(tmp_dir + '/dicts_for_2')

        assert os.path.exists(path_to_dict)
        assert os.path.exists(path_to_dict + "/1.dict")
        assert os.path.exists(path_to_dict + "/2.dict")

        assert not os.path.exists(path_to_dict + "/3.dict")

        assert os.path.islink(path_to_dict + "/1.dict")
        assert os.path.islink(path_to_dict + "/2.dict")

        assert file_get_contents(path_to_dict + "/1.dict") == "aaa\nbbb"
        assert file_get_contents(path_to_dict + "/2.dict") == "ccc\nddd"

    def test_build_hybride_dict(self):
        """ Test of dicts build mechanism for hybride attacks """
        if os.path.exists("/tmp/1/"):
            shutil.rmtree("/tmp/1/")
        os.mkdir("/tmp/1/")

        file_put_contents("/tmp/1/1.dict", "bbb\naaa\n")
        file_put_contents("/tmp/1/2.dict", "ddd\nccc\n")

        hybrite_dict_path = self.thrd.build_hybride_dict("/tmp/1/")
        assert os.path.exists(hybrite_dict_path)
        assert file_get_contents(hybrite_dict_path) == "aaa\nbbb\nccc\nddd\n"

    def test_build_cmd_dict(self):
        """ Building cmd for dict attack """
        dicts_path = Registry().get('config')['main']['dicts_path']

        self._add_dict_group()

        self._add_dict()
        self._add_dict(id=2, hash='2')
        file_put_contents(dicts_path + "/1.dict", "aaa\nbbb")
        file_put_contents(dicts_path + "/2.dict", "ccc\nddd")

        self._add_task(source=1)

        self.thrd.work_task['out_file'] = '/tmp/out.txt'
        self.thrd.work_task['session_name'] = '/tmp/session.txt'

        cmd = self.thrd.build_cmd(
            self.db.fetch_row("SELECT * FROM tasks WHERE id = 1"),
            1,
            '/tmp/test.txt'
        )

        assert cmd == [
            '{0}/cudaHashcat64.bin'.format(Registry().get('config')['main']['path_to_hc']), '-m900',
            '--outfile-format=5', '--status-automat',
            '--status-timer=4', '--status', '--potfile-disable', '--outfile=/tmp/out.txt', '--session=/tmp/session.txt',
            '-a0', '/tmp/test.txt', '/tmp//dicts_for_1/*.dict']

        self.thrd.work_task['out_file'] = '/tmp/out.txt'
        self.thrd.work_task['session_name'] = '/tmp/session.txt'

        self._add_rule()
        self.db.update("tasks", {"rule": 1}, "id = 1")
        cmd = self.thrd.build_cmd(
            self.db.fetch_row("SELECT * FROM tasks WHERE id = 1"),
            0,
            '/tmp/test.txt'
        )

        assert cmd == [
            '{0}/cudaHashcat64.bin'.format(Registry().get('config')['main']['path_to_hc']), '-m900',
            '--outfile-format=5', '--status-automat',
            '--status-timer=4', '--status', '--potfile-disable', '--outfile=/tmp/out.txt', '--session=/tmp/session.txt',
            '--restore', '-r /tmp/rules//1.rule', '-a0', '/tmp/test.txt', '/tmp//dicts_for_1/*.dict']

    def test_build_cmd_mask(self):
        """ Building cmd for mask attack """
        self._add_task(source='?l?d?u?s', type='mask')

        self.thrd.work_task['out_file'] = '/tmp/out.txt'
        self.thrd.work_task['session_name'] = '/tmp/session.txt'

        cmd = self.thrd.build_cmd(
            self.db.fetch_row("SELECT * FROM tasks WHERE id = 1"),
            1,
            '/tmp/test.txt'
        )

        assert cmd == [
            '{0}/cudaHashcat64.bin'.format(Registry().get('config')['main']['path_to_hc']), '-m900',
            '--outfile-format=5', '--status-automat',
            '--status-timer=4', '--status', '--potfile-disable', '--outfile=/tmp/out.txt', '--session=/tmp/session.txt',
            '-a3', '/tmp/test.txt', '?l?d?u?s']

        self.thrd.work_task['out_file'] = '/tmp/out.txt'
        self.thrd.work_task['session_name'] = '/tmp/session.txt'

        self.db.update(
            "tasks",
            {"custom_charset1": "abc", "custom_charset2": "def", "custom_charset3": "ghi", "custom_charset4": "klm",
             "increment": 1, "increment_min": 1, "increment_max": 2},
            "id = 1")

        cmd = self.thrd.build_cmd(
            self.db.fetch_row("SELECT * FROM tasks WHERE id = 1"),
            1,
            '/tmp/test.txt'
        )

        assert cmd == [
            '{0}/cudaHashcat64.bin'.format(Registry().get('config')['main']['path_to_hc']), '-m900',
            '--outfile-format=5', '--status-automat',
            '--status-timer=4', '--status', '--potfile-disable', '--outfile=/tmp/out.txt', '--session=/tmp/session.txt',
            '-a3', '--increment', '--increment-min=1', '--increment-max=2', '--custom-charset1=abc',
            '--custom-charset2=def', '--custom-charset3=ghi', '--custom-charset4=klm', '/tmp/test.txt', '?l?d?u?s']


    def test_build_cmd_hybride_maskdict(self):
        """ Building cmd for hybride (mask+dict) attack """
        dicts_path = Registry().get('config')['main']['dicts_path']

        self._add_dict_group()

        self._add_dict()
        self._add_dict(id=2, hash='2')
        file_put_contents(dicts_path + "/1.dict", "aaa\nbbb")
        file_put_contents(dicts_path + "/2.dict", "ccc\nddd")

        self._add_task(source=json.dumps({'mask':'?l?d?u?s', 'dict': 1}), type='maskdict')

        self.thrd.work_task['out_file'] = '/tmp/out.txt'
        self.thrd.work_task['session_name'] = '/tmp/session.txt'

        cmd = self.thrd.build_cmd(
            self.db.fetch_row("SELECT * FROM tasks WHERE id = 1"),
            1,
            '/tmp/test.txt'
        )

        assert cmd == [
            '{0}/cudaHashcat64.bin'.format(Registry().get('config')['main']['path_to_hc']), '-m900',
            '--outfile-format=5', '--status-automat',
            '--status-timer=4', '--status', '--potfile-disable', '--outfile=/tmp/out.txt', '--session=/tmp/session.txt',
            '-a7', '/tmp/test.txt', '?l?d?u?s', self.thrd.work_task['hybride_dict']]

        self.thrd.work_task['out_file'] = '/tmp/out.txt'
        self.thrd.work_task['session_name'] = '/tmp/session.txt'

        self.db.update(
            "tasks",
            {"custom_charset1": "abc", "custom_charset2": "def", "custom_charset3": "ghi", "custom_charset4": "klm",
             "increment": 1, "increment_min": 1, "increment_max": 2},
            "id = 1")

        cmd = self.thrd.build_cmd(
            self.db.fetch_row("SELECT * FROM tasks WHERE id = 1"),
            1,
            '/tmp/test.txt'
        )

        assert cmd == [
            '{0}/cudaHashcat64.bin'.format(Registry().get('config')['main']['path_to_hc']), '-m900',
            '--outfile-format=5', '--status-automat',
            '--status-timer=4', '--status', '--potfile-disable', '--outfile=/tmp/out.txt', '--session=/tmp/session.txt',
            '--custom-charset1=abc', '--custom-charset2=def', '--custom-charset3=ghi', '--custom-charset4=klm',
            '-a7', '/tmp/test.txt', '?l?d?u?s', self.thrd.work_task['hybride_dict']]

    def test_build_cmd_hybride_dictmask(self):
        """ Building cmd for hybride (dict+mask) attack """
        dicts_path = Registry().get('config')['main']['dicts_path']

        self._add_dict_group()

        self._add_dict()
        self._add_dict(id=2, hash='2')
        file_put_contents(dicts_path + "/1.dict", "aaa\nbbb")
        file_put_contents(dicts_path + "/2.dict", "ccc\nddd")

        self._add_task(source=json.dumps({'mask':'?l?d?u?s', 'dict': 1}), type='dictmask')

        self.thrd.work_task['out_file'] = '/tmp/out.txt'
        self.thrd.work_task['session_name'] = '/tmp/session.txt'

        cmd = self.thrd.build_cmd(
            self.db.fetch_row("SELECT * FROM tasks WHERE id = 1"),
            1,
            '/tmp/test.txt'
        )

        assert cmd == [
            '{0}/cudaHashcat64.bin'.format(Registry().get('config')['main']['path_to_hc']), '-m900',
            '--outfile-format=5', '--status-automat',
            '--status-timer=4', '--status', '--potfile-disable', '--outfile=/tmp/out.txt', '--session=/tmp/session.txt',
            '-a6', '/tmp/test.txt', self.thrd.work_task['hybride_dict'], '?l?d?u?s']

        self.thrd.work_task['out_file'] = '/tmp/out.txt'
        self.thrd.work_task['session_name'] = '/tmp/session.txt'

        self.db.update(
            "tasks",
            {"custom_charset1": "abc", "custom_charset2": "def", "custom_charset3": "ghi", "custom_charset4": "klm",
             "increment": 1, "increment_min": 1, "increment_max": 2},
            "id = 1")

        cmd = self.thrd.build_cmd(
            self.db.fetch_row("SELECT * FROM tasks WHERE id = 1"),
            1,
            '/tmp/test.txt'
        )

        assert cmd == [
            '{0}/cudaHashcat64.bin'.format(Registry().get('config')['main']['path_to_hc']), '-m900',
            '--outfile-format=5', '--status-automat',
            '--status-timer=4', '--status', '--potfile-disable', '--outfile=/tmp/out.txt', '--session=/tmp/session.txt',
            '--custom-charset1=abc', '--custom-charset2=def', '--custom-charset3=ghi', '--custom-charset4=klm',
            '-a6', '/tmp/test.txt', self.thrd.work_task['hybride_dict'], '?l?d?u?s']
