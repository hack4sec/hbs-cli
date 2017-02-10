# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Work thread
"""

import threading
import time
import os
import shutil
import re
import json

from subprocess import Popen, PIPE, check_output
from classes.Registry import Registry
from HbsException import HbsException

from libs.common import _d, gen_random_md5

class WorkerThread(threading.Thread):
    """ Main work thread - run hc, control work, etc """
    daemon = True
    work_task = None
    done = False
    _db = None
    status_time = 4
    out_buff_len = 600
    tmp_dir = None
    dicts_path = None
    path_to_hc = None
    hc_bin = None

    def __init__(self, work_task):
        threading.Thread.__init__(self)
        self.work_task = work_task
        self._db = Registry().get('db')

        config = Registry().get('config')
        self.tmp_dir = config['main']['tmp_dir']
        self.dicts_path = config['main']['dicts_path']
        self.outs_path = config['main']['outs_path']
        self.rules_path = config['main']['rules_path']
        self.path_to_hc = config['main']['path_to_hc']
        self.hc_bin = config['main']['hc_bin']

    def _clean_stdout_file(self):
        content = ""

        if os.path.exists(self.work_task['path_stdout']):
            fh = open(self.work_task['path_stdout'], 'r')
            while True:
                line = fh.readline()
                if line == '':
                    break

                if not re.match("^STATUS(.*)$", line) and len(line.strip()):
                    content += line

            while content.count("\n\n\n"):
                content = content.replace("\n\n\n", "\n")
            content = content.replace("\r", "")

            fh.close()

        fh = open(self.work_task['path_stdout'], 'w')
        fh.write(content)
        fh.close()

    def _refresh_work_task(self):
        self.work_task = self._db.fetch_row(
            "SELECT * FROM task_works WHERE id = {0}".format(self.work_task['id'])
        )

    def _not_high_priority(self):
        return self._db.fetch_one(
            ("SELECT tw.id FROM task_works tw, hashlists hl "
             "WHERE tw.hashlist_id = hl.id  AND tw.priority > {0} AND tw.status='wait' AND tw.id != {1} "
             "AND hl.alg_id NOT IN( "
             "  SELECT hl.alg_id FROM `task_works` tw, hashlists hl, algs a "
             "  WHERE tw.hashlist_id = hl.id AND hl.alg_id = a.id AND tw.status IN('waitoutparse', 'outparsing')"
             ")"
             "ORDER BY tw.priority DESC LIMIT 1")
            .format(
                self.work_task['priority'],
                self.work_task['id']
            )
        )

    def _update_hc_status(self, status_row):
        hc_status, hc_speed, hc_curku, hc_progress, hc_rechash, hc_recsalt, hc_temp = status_row
        self._db.q(
            ("UPDATE task_works SET "
             "hc_status = {0}, hc_speed = {1}, hc_curku = {2}, hc_progress = {3}, hc_rechash = {4}, hc_temp = {5} "
             "WHERE id = {6}")
            .format(
                self._db.quote(hc_status),
                self._db.quote(hc_speed),
                self._db.quote(hc_curku),
                self._db.quote(hc_progress),
                self._db.quote(hc_rechash),
                self._db.quote(hc_temp),
                self.work_task['id']
            )
        )

    def _update_task_props(self, data):
        self._db.update('task_works', data, "id = {0}".format(self.work_task['id']))
        self._refresh_work_task()

    def _make_hashlist(self):
        path_to_hashlist = self.tmp_dir + "/" + gen_random_md5()
        fh = open(path_to_hashlist, 'w')
        res = self._db.q(
            ("SELECT IF(LENGTH(salt), CONCAT(`hash`, ':', salt), hash) as hash "
             "FROM `hashes` WHERE hashlist_id={0} AND cracked = 0")
            .format(
                self.work_task['hashlist_id']
            )
        )
        for _hash in res:
            fh.write(_hash[0] + "\n")
        fh.close()

        return path_to_hashlist

    def _calc_hashes_before(self):
        self._db.q(
            "UPDATE task_works SET uncracked_before = "
            "(SELECT COUNT(id) FROM hashes WHERE hashlist_id = {0} AND cracked = 0) "
            "WHERE id = {1}".format(self.work_task['hashlist_id'], self.work_task['id'])
        )

    def _change_task_status(self, stop_by_priority, process_stoped):
        if stop_by_priority:
            self._db.q("UPDATE task_works SET status='wait' WHERE id = {0}".format(self.work_task['id']))
        else:
            self._db.q(
                "UPDATE task_works SET status='{0}' WHERE id = {1}".format(
                    ('stop' if process_stoped else 'waitoutparse'), self.work_task['id']
                )
            )

    def get_task_data_by_id(self, task_id):
        return self._db.fetch_row("SELECT * FROM tasks WHERE id = {0}".format(task_id))

    def _add_custom_charsets_to_cmd(self, task, cmd_to_run):
        for i in range(1, 5):
            if task['custom_charset{0}'.format(i)] is not None and len(task['custom_charset{0}'.format(i)]):
                cmd_to_run.append("--custom-charset{0}=".format(i) + task['custom_charset{0}'.format(i)])
        return cmd_to_run

    def _add_increment_to_cmd(self, task, cmd_to_run):
        if task['increment']:
            if int(task['increment_min']) > int(task['increment_max']):
                raise HbsException(
                    "Wrong increment - from {0} to {1}".format(
                        int(task['increment_min']),
                        int(task['increment_max'])
                    )
                )

            cmd_to_run.append("--increment")
            cmd_to_run.append("--increment-min=" + str(task['increment_min']))
            cmd_to_run.append("--increment-max=" + str(task['increment_max']))
        return cmd_to_run

    def _build_dicts(self, task_is_new, task):
        tmp_dicts_dir = self.tmp_dir + "/dicts_for_{0}".format(self.work_task['id'])

        if task_is_new or not os.path.exists(tmp_dicts_dir):
            dicts = self._db.fetch_all("SELECT * FROM dicts WHERE group_id = {0}".format(
                task['source'] if task['type'] == 'dict' else json.loads(task['source'])['dict']
            ))

            self._update_task_props({'process_status': "preparedicts"})
            _d("worker", "Create symlinks dicts dir {0}".format(tmp_dicts_dir))

            if os.path.exists(tmp_dicts_dir):
                _d("worker", "Remove old symlinks dicts dir {0}".format(tmp_dicts_dir))
                shutil.rmtree(tmp_dicts_dir)
            os.mkdir(tmp_dicts_dir)

            for _dict in dicts:
                os.symlink(
                    "{0}/{1}.dict".format(self.dicts_path, _dict['hash']),
                    "{0}/{1}.dict".format(tmp_dicts_dir, _dict['hash'])
                )

        return tmp_dicts_dir

    def _build_hybride_dict(self, tmp_dicts_dir):
        _d("worker", "Compile hybride dict with cmd: ", False)
        path_to_hybride_dict = "{0}/{1}.hybride".format(self.tmp_dir, gen_random_md5())

        cat_cmd = "cat {0}/* > {1}-unsorted".format(tmp_dicts_dir, path_to_hybride_dict)
        _d("worker", "'{0}'".format(cat_cmd), prefix=False)
        check_output(cat_cmd, shell=True)

        sort_cmd = "sort {0}-unsorted > {0}".format(path_to_hybride_dict)
        _d("worker", "'{0}'".format(sort_cmd), prefix=False)
        check_output(sort_cmd, shell=True)

        os.remove("{0}-unsorted".format(path_to_hybride_dict))

        _d("worker", "Cat and sort done".format(sort_cmd))

        return path_to_hybride_dict


    # Словарная - если словари были, а их снесли
    def _build_cmd(self, task, task_is_new, path_to_hashlist):
        alg_id = self._db.fetch_one(
            "SELECT h.alg_id FROM hashlists h WHERE h.id = {0}".format(self.work_task['hashlist_id'])
        )

        cmd_template = [
            "{0}/{1}".format(self.path_to_hc, self.hc_bin),
            "-m{0}".format(alg_id),
            "--outfile-format=5",
            "--status-automat",
            "--status-timer={0}".format(self.status_time),
            "--status",
            "--potfile-disable",
            "--outfile={0}".format(self.work_task['out_file'])
        ]

        if len(task['additional_params']):
            cmd_template.append(task['additional_params'])

        cmd_template.append("--session={0}".format(self.work_task['session_name']))
        if not task_is_new:
            _d("worker", "Restore {0}".format(self.work_task['session_name']))
            cmd_template.append("--restore")

        if task['type'] == 'dict':
            if task['rule']:
                rule_hash = self._db.fetch_one("SELECT hash FROM rules WHERE id = " + str(task['rule']))
                cmd_template.append("-r {0}".format(self.rules_path + "/" + rule_hash))

            tmp_dicts_dir = self._build_dicts(task_is_new, task)

            cmd_to_run = list(cmd_template)
            cmd_to_run.extend(
                [
                    "-a0",
                    path_to_hashlist,
                    "{0}/*.dict".format(tmp_dicts_dir)
                ]
            )
        elif task['type'] == 'mask':
            cmd_to_run = list(cmd_template)
            cmd_to_run.append("-a3")
            cmd_to_run = self._add_increment_to_cmd(task, cmd_to_run)
            cmd_to_run = self._add_custom_charsets_to_cmd(task, cmd_to_run)
            cmd_to_run.extend([
                path_to_hashlist,
                task['source'],
            ])
        elif task['type'] == 'dictmask' or task['type'] == 'maskdict':
            tmp_dicts_dir = self._build_dicts(task_is_new, task)
            if task_is_new or not os.path.exists(tmp_dicts_dir):
                path_to_hybride_dict = self._build_hybride_dict(tmp_dicts_dir)
                self._update_task_props({'hybride_dict': path_to_hybride_dict})
            else:
                path_to_hybride_dict = self.work_task['hybride_dict']

            cmd_to_run = self._add_custom_charsets_to_cmd(task, list(cmd_template))

            cmd_to_run.extend(
                [
                    "-a6" if task['type'] == 'dictmask' else "-a7",
                    path_to_hashlist,
                    path_to_hybride_dict if task['type'] == 'dictmask' else json.loads(task['source'])['mask'],
                    json.loads(task['source'])['mask'] if task['type'] == 'dictmask' else path_to_hybride_dict
                ]
            )

        return cmd_to_run


    def run(self):
        """ Start method of thread """
        _d("worker", "Run thread with work_task id: {0}".format(self.work_task['id']))

        task_is_new = not len(self.work_task['session_name'])
        if task_is_new:
            session_name = gen_random_md5()
            path_stdout = "{0}/{1}.output".format(self.outs_path, gen_random_md5())
            out_file = "{0}/{1}.out".format(self.tmp_dir, gen_random_md5())
            self._update_task_props(
                {
                    'status': 'work',
                    'session_name': session_name,
                    'path_stdout': path_stdout,
                    'out_file': out_file,
                    'hc_status': '',
                    'hc_speed': '',
                    'hc_curku': '',
                    'hc_progress': '',
                    'hc_rechash': '',
                    'hc_temp': '',
                    'stderr': '',
                }
            )
            self._calc_hashes_before()
        else:
            path_stdout = self.work_task['path_stdout']

        fh_output = open(path_stdout, 'a')
        if not task_is_new:
            fh_output.write('\n\n')

        os.chdir(self.path_to_hc)

        task = self.get_task_data_by_id(self.work_task['task_id'])
        _d("worker", "Source task id/source: {0}/{1}/{2}".format(task['id'], task['type'], task['source']))

        self._update_task_props({'process_status': "buildhashlist"})
        path_to_hashlist = self._make_hashlist()
        _d("worker", "Hashlist created")

        self._update_task_props({'process_status': "compilecommand"})
        _d("worker", "Compile commands")

        cmd_to_run = self._build_cmd(task, task_is_new, path_to_hashlist)

        _d("worker", "Will run: ")
        _d("worker", " ".join(cmd_to_run), prefix=False)
        fh_output.write(" ".join(cmd_to_run) + "\n")

        stime = int(time.time())

        process_stoped = False
        stop_by_priority = False

        self._update_task_props({'process_status': "starting"})

        p = Popen(" ".join(cmd_to_run), stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
        while p.poll() is None:
            self._refresh_work_task()

            if self.work_task['status'] in ['go_stop', 'stop']:
                _d("worker", "Stop signal ")
                p.stdin.write('q')
                process_stoped = True

            if self._not_high_priority():
                stop_by_priority = True
                _d("worker", "Have most priority task: {0}".format(self._not_high_priority()))
                p.stdin.write('q')
                process_stoped = True

            output = p.stdout.read(self.out_buff_len)
            if len(output.strip()):
                fh_output.write(output)

            rows = re.findall(
                "STATUS(.*)SPEED(.*)CURKU(.*)PROGRESS(.*)RECHASH(.*)RECSALT(.*)TEMP(.*)",
                output
            )

            if len(rows):
                if self.work_task['process_status'] != 'work':
                    self._update_task_props({'process_status': "work"})
                self._update_hc_status(map(str.strip, rows[-1]))

            time.sleep(self.status_time/2)

        fh_output.write(p.stdout.read())
        self._update_task_props({'work_time': int(self.work_task['work_time']) + (int(time.time())-stime)})

        stderr = p.stderr.read()
        if len(stderr.strip()):
            self._update_task_props({'stderr': stderr.strip()})
            fh_output.write('\n' + stderr)

        fh_output.close()

        _d("worker", "Task done, wait load cracked hashes, worker go to next task")

        _d("worker", "Change task status")
        self._change_task_status(stop_by_priority, process_stoped)

        _d("worker", "Clean file with stdout")
        self._clean_stdout_file()

        if self.work_task['status'] == 'done' and \
                len(self.work_task['hybride_dict']) and \
                os.path.exists(self.work_task['hybride_dict']):
            os.remove(self.work_task['hybride_dict'])
            self._update_task_props({'hybride_dict': ''})

        _d("worker", "Done\n")
        self.done = True

