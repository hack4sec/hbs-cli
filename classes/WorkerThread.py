# -*- coding: utf-8 -*-
""" Work thread """

import threading
import hashlib
import time
import random
import sys
import os
import shutil
import re
import json

from subprocess import Popen, PIPE, check_output
from Registry import Registry

from libs.common import _d

class WorkerThread(threading.Thread):
    """ Api for work with DB """
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

    def run(self):
        """ Start method of thread """
        _d("worker", "Run thread with work_task id: {0}".format(self.work_task['id']))

        task_is_new = not len(self.work_task['session_name'])
        session_name = self.work_task['session_name'] if not task_is_new else self._gen_random_md5()
        path_stdout = self.work_task['path_stdout'] if not task_is_new else "{0}/{1}.output".format(
            self.outs_path, self._gen_random_md5()
        )
        self._update_task_props(
            {
                'status': 'work',
                'session_name': session_name,
                'path_stdout': path_stdout,
                'hc_status': '',
                'hc_speed': '',
                'hc_curku': '',
                'hc_progress': '',
                'hc_rechash': '',
                'hc_temp': '',
                'stderr': '',
            }
        )

        fh_output = open(path_stdout, 'a')
        if not task_is_new:
            fh_output.write('\n\n')

        os.chdir(self.path_to_hc)

        task = self._db.fetch_row("SELECT * FROM tasks WHERE id = " + str(self.work_task['task_id']))
        _d("worker", "Source task id/source: {0}/{1}/{2}".format(task['id'], task['type'], task['source']))

        self._update_task_props({'process_status': "buildhashlist"})
        path_to_hashlist = self._make_hashlist()
        _d("worker", "Hashlist created")
        self._update_task_props({'process_status': "compilecommand"})

        # Updated hash before
        if task_is_new:
            self._calc_hashes_before()

        alg_id = self._db.fetch_one(
            "SELECT a.alg_id FROM hashlists h, algs a WHERE h.id = {0} AND h.alg_id = a.id "
            .format(self.work_task['hashlist_id'])
        )
        _d("worker", "Compile commands")

        if not len(self.work_task['out_file']):
            self._update_task_props({'out_file': "{0}/{1}.out".format(self.tmp_dir, self._gen_random_md5())})

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

        cmd_template.append("--session={0}".format(session_name))
        if not task_is_new:
            _d("worker", "Restore {0}".format(session_name))
            cmd_template.append("--restore")

        if task['type'] == 'dict':
            dicts = self._db.fetch_all("SELECT * FROM dicts WHERE group_id = " + task['source'])

            if task['rule']:
                rule_hash = self._db.fetch_one("SELECT hash FROM rules WHERE id = " + str(task['rule']))
                cmd_template.append("-r {0}".format(self.rules_path + "/" + rule_hash))

            tmp_dicts_dir = self.tmp_dir + "/dicts_for_{0}".format(self.work_task['id'])
            if task_is_new:
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

            if task['increment']:
                cmd_to_run.append("--increment")
                cmd_to_run.append("--increment-min=" + str(task['increment_min']))
                cmd_to_run.append("--increment-max=" + str(task['increment_max']))

            if len(task['custom_charset1']):
                cmd_to_run.append("--custom-charset1=" + task['custom_charset1'])
            if len(task['custom_charset2']):
                cmd_to_run.append("--custom-charset2=" + task['custom_charset2'])
            if len(task['custom_charset3']):
                cmd_to_run.append("--custom-charset3=" + task['custom_charset3'])
            if len(task['custom_charset4']):
                cmd_to_run.append("--custom-charset4=" + task['custom_charset4'])

            cmd_to_run.extend([
                path_to_hashlist,
                task['source'],
            ])
        elif task['type'] == 'dictmask' or task['type'] == 'maskdict':
            dicts = self._db.fetch_all("SELECT * FROM dicts WHERE group_id = " + json.loads(task['source'])['dict'])
            tmp_dicts_dir = self.tmp_dir + "/dicts_for_{0}".format(self.work_task['id'])
            if task_is_new:
                self._update_task_props({'process_status': "compilehybride"})
                _d("worker", "Gen hybride dict")
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

                _d("worker", "Compile hybride dict with cmd: ", False)
                path_to_hybride_dict = "{0}/{1}.hybride".format(self.tmp_dir, self._gen_random_md5())
                _d("worker", "'cat {0}/* > {1}'".format(tmp_dicts_dir, path_to_hybride_dict), prefix=False)
                check_output(
                    "cat {0}/* > {1}".format(
                        tmp_dicts_dir,
                        path_to_hybride_dict
                    ),
                    shell=True
                )
                self._update_task_props({'hybride_dict': path_to_hybride_dict})
            else:
                path_to_hybride_dict = self.work_task['hybride_dict']


            cmd_to_run = list(cmd_template)

            if len(task['custom_charset1']):
                cmd_to_run.append("--custom-charset1=" + task['custom_charset1'])
            if len(task['custom_charset2']):
                cmd_to_run.append("--custom-charset2=" + task['custom_charset2'])
            if len(task['custom_charset3']):
                cmd_to_run.append("--custom-charset3=" + task['custom_charset3'])
            if len(task['custom_charset4']):
                cmd_to_run.append("--custom-charset4=" + task['custom_charset4'])

            cmd_to_run.extend(
                [
                    "-a6" if task['type'] == 'dictmask' else "-a7",
                    path_to_hashlist,
                    path_to_hybride_dict if task['type'] == 'dictmask' else json.loads(task['source'])['mask'],
                    json.loads(task['source'])['mask'] if task['type'] == 'dictmask' else path_to_hybride_dict
                ]
            )

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
            #print output;sys.stdout.flush()

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

    def _clean_stdout_file(self):
        fh = open(self.work_task['path_stdout'], 'r')
        content = ""
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

    def _md5(self, string):
        m = hashlib.md5()
        m.update(string.encode('UTF-8'))
        return m.hexdigest()

    def _refresh_work_task(self):
        self.work_task = self._db.fetch_row(
            "SELECT * FROM task_works WHERE id = {0}".format(self.work_task['id'])
        )

    def _not_high_priority(self):
        return self._db.fetch_one(
            ("SELECT id FROM task_works "
             "WHERE priority > {0} AND status='wait' AND id != {1} "
             "ORDER BY priority DESC LIMIT 1")
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

    def _gen_random_md5(self):
        return self._md5(str(time.time()) + str(random.randint(0, 9999999)))

    def _update_task_props(self, data):
        self._db.update('task_works', data, "id = {0}".format(self.work_task['id']))
        self._refresh_work_task()

    def _make_hashlist(self):
        path_to_hashlist = self.tmp_dir + "/" + self._gen_random_md5()
        fh = open(path_to_hashlist, 'w')
        res = self._db.q(
            ("SELECT IF(LENGTH(salt), CONCAT(`hash`, ':', salt), hash) as hash "
             "FROM `hashes` WHERE hashlist_id={0} AND !cracked")
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
            "(SELECT COUNT(id) FROM hashes WHERE hashlist_id = {0} AND !cracked) "
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

    def _parse_outfile(self):
        self._refresh_work_task()

        if os.path.exists(self.work_task['out_file']):
            fh = open(self.work_task['out_file'], 'r')
            while True:
                line = fh.readline()
                if not line:
                    break
                line = line.strip()

                password = line[line.rfind(":")+1:].strip().decode("hex")
                summ = self._md5(line[:line.rfind(":")])

                self._db.q(
                    "UPDATE hashes SET password = {0}, cracked = 1 WHERE hashlist_id = {1} AND summ={2}"
                    .format(
                        self._db.quote(password),
                        self.work_task['hashlist_id'],
                        self._db.quote(summ),
                    )
                )

                #if line.count(":") == 1:
                #    hash, password = line.split(":")
                #    salt = ''
                #elif line.count(":") == 2:
                #    hash, password, salt = line.split(":")
                #else:
                #    self._update_task_props({'err_output': self.work_task['err_output'] + '\n' + line})
                #
                #self._db.q(
                #    ("UPDATE hashes SET password = {3}, cracked = 1"
                #     "WHERE hashlist_id = {0} AND hash = {1} AND salt={2} AND !cracked")
                #     .format(
                #            self.work_task['hashlist_id'],
                #            self._db.quote(hash),
                #            self._db.quote(salt),
                #            self._db.quote(password)
                #    )
                #)
        else:
            _d("worker", "Outfile {0} not exists".format(self.work_task['out_file']))
