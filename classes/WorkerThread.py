# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Work thread
"""


import time
import os
import shutil
import re
import json
import traceback

from subprocess import Popen, PIPE, check_output
from classes.Registry import Registry
from classes.HbsException import HbsException
from classes.Factory import Factory
from classes.CommonThread import CommonThread

from libs.common import gen_random_md5

class WorkerThread(CommonThread):
    """ Main work thread - run hc, control work, etc """
    work_task = None
    done = False
    _db = None
    status_time = 4
    out_buff_len = 600
    tmp_dir = None
    dicts_path = None
    path_to_hc = None
    hc_bin = None

    thread_name = "worker"

    def __init__(self, work_task):
        """
        Initialization
        :param work_task: Work task row (named dict from db)
        """
        CommonThread.__init__(self)
        self.work_task = work_task
        self._db = Factory().new_db_connect()

        config = Registry().get('config')
        self.tmp_dir = config['main']['tmp_dir']
        self.dicts_path = config['main']['dicts_path']
        self.outs_path = config['main']['outs_path']
        self.rules_path = config['main']['rules_path']
        self.path_to_hc = config['main']['path_to_hc']
        self.hc_bin = config['main']['hc_bin']

    def clean_stdout_file(self):
        """ Clean stdout file from status-automate entries """
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

    def refresh_work_task(self):
        """ Refresh current work task data """
        self.work_task = self._db.fetch_row(
            "SELECT * FROM task_works WHERE id = {0}".format(self.work_task['id'])
        )

    def not_high_priority(self):
        """
        Is current task a most priority?
        :return int: Id of most priority task
        """
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

    def update_hc_status(self, status_row):
        """
        Update hc-data of current task - temp, progress, speed, etc
        :param status_row: list with status data
        :return:
        """
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

    def update_task_props(self, data):
        """
        Update task properties
        :param data: Named dict with update data
        :return:
        """
        self._db.update('task_works', data, "id = {0}".format(self.work_task['id']))
        self.refresh_work_task()

    def make_hashlist(self):
        """
        Build txt hashlist from database
        :return str: Path to txt hashlist
        """
        path_to_hashlist = self.tmp_dir + "/" + gen_random_md5()
        fh = open(path_to_hashlist, 'w')
        res = self._db.q(
            ("SELECT IF(LENGTH(salt), CONCAT(`hash`, ':', salt), hash) as hash "
             "FROM `hashes` WHERE hashlist_id={0} AND cracked = 0")
            .format(
                self.work_task['hashlist_id']
            ),
            True
        )
        for _hash in res:
            fh.write(_hash[0] + "\n")
        fh.close()

        return path_to_hashlist

    def calc_hashes_before(self):
        """ Calculate uncracked hashes count before task run """
        self._db.q(
            "UPDATE task_works SET uncracked_before = "
            "(SELECT COUNT(id) FROM hashes WHERE hashlist_id = {0} AND cracked = 0) "
            "WHERE id = {1}".format(self.work_task['hashlist_id'], self.work_task['id'])
        )

    def change_task_status(self, stop_by_priority, process_stoped):
        """
        Change task status when it stop (set stop, wait or waitoutparse)
        :param stop_by_priority:
        :param process_stoped:
        :return:
        """
        if stop_by_priority:
            self._db.q("UPDATE task_works SET status='wait' WHERE id = {0}".format(self.work_task['id']))
        else:
            self._db.q(
                "UPDATE task_works SET status='{0}' WHERE id = {1}".format(
                    ('stop' if process_stoped else 'waitoutparse'), self.work_task['id']
                )
            )

    def get_task_data_by_id(self, task_id):
        """
        Get task row by id
        :param task_id:
        :return dict: Named dict with task data
        """
        return self._db.fetch_row("SELECT * FROM tasks WHERE id = {0}".format(task_id))

    def add_custom_charsets_to_cmd(self, task, cmd_to_run):
        """
        Add custom charsets to cmd
        :param task: Task row
        :param cmd_to_run: cmd for change
        :return:
        """
        for i in range(1, 5):
            if task['custom_charset{0}'.format(i)] is not None and len(task['custom_charset{0}'.format(i)]):
                cmd_to_run.append("--custom-charset{0}=".format(i) + task['custom_charset{0}'.format(i)])
        return cmd_to_run

    def add_increment_to_cmd(self, task, cmd_to_run):
        """
        Adding increment params to cmd
        :param task: Task row
        :param cmd_to_run: cmd for change
        :return:
        """
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

    def build_dicts(self, task_is_new, task):
        """
        Build symlinks on need dicts group
        :param task_is_new: is this task new? (dicts already done)
        :param task: task row
        :return:
        """
        tmp_dicts_dir = self.tmp_dir + "/dicts_for_{0}".format(self.work_task['id'])

        if task_is_new or not os.path.exists(tmp_dicts_dir):
            dicts = self._db.fetch_all("SELECT * FROM dicts WHERE group_id = {0}".format(
                task['source'] if task['type'] == 'dict' else json.loads(task['source'])['dict']
            ))

            self.update_task_props({'process_status': "preparedicts"})
            Registry().get('logger').log("worker", "Create symlinks dicts dir {0}".format(tmp_dicts_dir))

            if os.path.exists(tmp_dicts_dir):
                Registry().get('logger').log("worker", "Remove old symlinks dicts dir {0}".format(tmp_dicts_dir))
                shutil.rmtree(tmp_dicts_dir)
            os.mkdir(tmp_dicts_dir)

            for _dict in dicts:
                os.symlink(
                    "{0}/{1}.dict".format(self.dicts_path, _dict['hash']),
                    "{0}/{1}.dict".format(tmp_dicts_dir, _dict['hash'])
                )

        return tmp_dicts_dir

    def build_hybride_dict(self, tmp_dicts_dir):
        """
        Build single big dict for hybride attacks
        :param tmp_dicts_dir:
        :return str: path to dict
        """
        path_to_hybride_dict = "{0}/{1}.hybride".format(self.tmp_dir, gen_random_md5())

        cat_cmd = "cat {0}/* > {1}-unsorted".format(tmp_dicts_dir, path_to_hybride_dict)
        Registry().get('logger').log("worker", "Compile hybride dict by cmd: \n{0}".format(cat_cmd))
        check_output(cat_cmd, shell=True)

        sort_cmd = "sort {0}-unsorted > {0}".format(path_to_hybride_dict)
        Registry().get('logger').log("worker", "Sort dict by cmd: \n{0}".format(sort_cmd))
        check_output(sort_cmd, shell=True)

        os.remove("{0}-unsorted".format(path_to_hybride_dict))

        Registry().get('logger').log("worker", "Cat and sort done".format(sort_cmd))

        return path_to_hybride_dict

    def build_cmd(self, task, task_is_new, path_to_hashlist):
        """
        Build shell cmd for hc run
        :param task: task row
        :param task_is_new: is task new?
        :param path_to_hashlist: path to txt hashlist
        :return:
        """
        alg_id = self._db.fetch_one(
            "SELECT a.alg_id FROM hashlists h, algs a WHERE h.id = {0} AND h.alg_id = a.id "
            .format(self.work_task['hashlist_id'])
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
            Registry().get('logger').log("worker", "Restore {0}".format(self.work_task['session_name']))
            cmd_template.append("--restore")

        if task['type'] == 'dict':
            if task['rule']:
                rule_hash = self._db.fetch_one("SELECT hash FROM rules WHERE id = " + str(task['rule']))
                cmd_template.append("-r {0}".format(self.rules_path + "/" + rule_hash))

            tmp_dicts_dir = self.build_dicts(task_is_new, task)

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
            cmd_to_run = self.add_increment_to_cmd(task, cmd_to_run)
            cmd_to_run = self.add_custom_charsets_to_cmd(task, cmd_to_run)
            cmd_to_run.extend([
                path_to_hashlist,
                task['source'],
            ])
        elif task['type'] == 'dictmask' or task['type'] == 'maskdict':
            tmp_dicts_dir = self.build_dicts(task_is_new, task)
            if task_is_new or not os.path.exists(tmp_dicts_dir):
                path_to_hybride_dict = self.build_hybride_dict(tmp_dicts_dir)
                self.update_task_props({'hybride_dict': path_to_hybride_dict})
            else:
                path_to_hybride_dict = self.work_task['hybride_dict']

            cmd_to_run = self.add_custom_charsets_to_cmd(task, list(cmd_template))

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
        try:
            Registry().get('logger').log("worker", "Run thread with work_task id: {0}".format(self.work_task['id']))

            uncracked_in_hashlist = self._db.fetch_one(
                "SELECT uncracked FROM hashlists WHERE id = {0}".format(self.work_task['hashlist_id']))
            if uncracked_in_hashlist == 0:
                self._db.q("UPDATE task_works SET status='done' WHERE id = {0}".format(self.work_task['id']))
                Registry().get('logger').log(
                    "worker",
                    "Work task {0} blank, because hashlist {1} not contains uncracked hashes".format(
                        self.work_task['id'], self.work_task['hashlist_id']))
                self.done = True
                return

            task_is_new = not len(self.work_task['session_name'])
            if task_is_new:
                session_name = gen_random_md5()
                path_stdout = "{0}/{1}.output".format(self.outs_path, gen_random_md5())
                out_file = "{0}/{1}.out".format(self.tmp_dir, gen_random_md5())
                self.update_task_props(
                    {
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
                self.calc_hashes_before()
            else:
                path_stdout = self.work_task['path_stdout']

            self.update_task_props({'status': 'work'})

            fh_output = open(path_stdout, 'a')
            if not task_is_new:
                fh_output.write('\n\n')

            os.chdir(self.path_to_hc)

            task = self.get_task_data_by_id(self.work_task['task_id'])
            Registry().get('logger').log("worker",
                                         "Source task id/source: {0}/{1}/{2}".format(
                                             task['id'], task['type'], task['source']))

            self.update_task_props({'process_status': "buildhashlist"})
            path_to_hashlist = self.make_hashlist()
            Registry().get('logger').log("worker", "Hashlist created")

            self.update_task_props({'process_status': "compilecommand"})
            Registry().get('logger').log("worker", "Compile command")

            cmd_to_run = self.build_cmd(task, task_is_new, path_to_hashlist)

            Registry().get('logger').log("worker", "Will run: " + " ".join(cmd_to_run))
            fh_output.write(" ".join(cmd_to_run) + "\n")

            stime = int(time.time())

            process_stoped = False
            stop_by_priority = False

            self.update_task_props({'process_status': "starting"})

            p = Popen(" ".join(cmd_to_run), stdout=PIPE, stdin=PIPE, stderr=PIPE, shell=True)
            while p.poll() is None:
                self.refresh_work_task()

                if not process_stoped and self.work_task['status'] in ['go_stop', 'stop']:
                    Registry().get('logger').log("worker", "Stop signal ")
                    p.stdin.write('q')
                    process_stoped = True

                if self.not_high_priority():
                    stop_by_priority = True
                    Registry().get('logger').log("worker", "Have most priority task: {0}".format(self.not_high_priority()))
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
                        self.update_task_props({'process_status': "work"})
                    self.update_hc_status(map(str.strip, rows[-1]))

                time.sleep(self.status_time/2)

            fh_output.write(p.stdout.read())
            self.update_task_props({'work_time': int(self.work_task['work_time']) + (int(time.time()) - stime)})

            stderr = p.stderr.read()
            if len(stderr.strip()):
                self.update_task_props({'stderr': stderr.strip()})
                fh_output.write('\n' + stderr)

            fh_output.close()

            Registry().get('logger').log("worker", "Task done, wait load cracked hashes, worker go to next task")

            Registry().get('logger').log("worker", "Change task status")
            self.change_task_status(stop_by_priority, process_stoped)

            Registry().get('logger').log("worker", "Clean file with stdout")
            self.clean_stdout_file()

            if self.work_task['status'] == 'waitoutparse':
                session_file = "{0}/{1}.restore".format(self.path_to_hc, self.work_task['session_name'])
                if os.path.exists(session_file):
                    os.remove(session_file)
                log_file = "{0}/{1}.log".format(self.path_to_hc, self.work_task['session_name'])
                if os.path.exists(log_file):
                    os.remove(log_file)

            if self.work_task['status'] == 'waitoutparse' and \
                    len(self.work_task['hybride_dict']) and \
                    os.path.exists(self.work_task['hybride_dict']):
                os.remove(self.work_task['hybride_dict'])
                self.update_task_props({'hybride_dict': ''})

            if self.work_task['status'] == 'waitoutparse':
                Registry().get('logger').log("worker", "Work task {0} done\n".format(self.work_task['id']))
            elif self.work_task['status'] == 'wait':
                Registry().get('logger').log("worker", "Work task {0} return to wait\n".format(self.work_task['id']))
            elif self.work_task['status'] == 'stop':
                Registry().get('logger').log("worker", "Work task {0} stopped\n".format(self.work_task['id']))

            self.done = True
        except BaseException as ex:
            self.exception(ex)

