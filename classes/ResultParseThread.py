# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Thread for hc results parsing
"""

import time
import os
import threading

from classes.Registry import Registry
from classes.Factory import Factory
from classes.Logger import Logger
from classes.HbsException import HbsException
from libs.common import md5, update_hashlist_counts


class ResultParseThread(threading.Thread):
    """ Thread for hc results parsing """
    current_work_task_id = None
    daemon = True
    delay_per_check = None
    available = True

    def __init__(self):
        """ Initialization """
        threading.Thread.__init__(self)
        self._db = Factory().new_db_connect()

        config = Registry().get('config')
        self.tmp_dir = config['main']['tmp_dir']
        self.dicts_path = config['main']['dicts_path']
        self.outs_path = config['main']['outs_path']
        self.rules_path = config['main']['rules_path']
        self.path_to_hc = config['main']['path_to_hc']
        self.hc_bin = config['main']['hc_bin']
        self.delay_per_check = int(config['main']['results_parser_delay_per_try'])

    def update_status(self, status):
        """
        Update work task status
        :param status: String status
        :return:
        """
        self.update_work_task_field('status', status)

    def get_work_task_data(self):
        """
        Get work task data from db
        :return dict: Named dict with data
        """
        return self._db.fetch_row("SELECT * FROM task_works WHERE id = {0}".format(self.get_current_work_task_id()))

    def update_work_task_field(self, field, value):
        """
        Update one field of current work task
        :param field:
        :param value:
        :return:
        """
        self._db.update("task_works", {field: value}, "id = {0}".format(self.get_current_work_task_id()))

    def update_all_hashlists_counts_by_alg_id(self, alg_id):
        """
        Update cracked and uncracked hashes counts for all hashlists
        :param alg_id:
        :return:
        """
        for _id in self._db.fetch_col("SELECT id FROM hashlists WHERE alg_id = {0}".format(int(alg_id))):
            update_hashlist_counts(self._db, _id)

    def get_current_work_task_id(self):
        """
        Return id of current work task
        :exception HbsException: if current work task id not set
        :return int:
        """
        if self.current_work_task_id is None:
            raise HbsException("Current task for work not set")
        return self.current_work_task_id

    def get_waiting_task_for_work(self):
        """
        Return worktask id ready for work
        :return int:
        """
        self.current_work_task_id = self._db.fetch_one(
            "SELECT id FROM task_works WHERE status='waitoutparse' ORDER BY id ASC LIMIT 1"
        )
        return self.current_work_task_id

    def get_hashlist_data(self, hashlist_id):
        """
        Return hashlist row
        :param hashlist_id:
        :return dict: hashlist data
        """
        return self._db.fetch_row("SELECT * FROM hashlists WHERE id = {0}".format(hashlist_id))

    def parse_outfile_and_fill_found_hashes(self, work_task, hashlist):
        """
        Parse outfile from hc and put found hashes in db
        :param work_task: worktask row
        :param hashlist: hashlist row
        :return:
        """
        out_file_fh = open(work_task['out_file'], 'r')
        for _line in out_file_fh:
            _line = _line.strip()

            password = _line[_line.rfind(":") + 1:].strip().decode("hex")
            summ = md5(_line[:_line.rfind(":")])

            self._db.q(
                "UPDATE `hashes` h, hashlists hl "
                "SET h.`password` = {0}, h.cracked = 1 "
                "WHERE h.hashlist_id = hl.id AND hl.alg_id = {1} AND h.summ = {2} AND h.cracked = 0"
                .format(self._db.quote(password), hashlist['alg_id'], self._db.quote(summ))
            )

    def update_task_uncracked_count(self, work_task_id, hashlist_id):
        """
        Update uncraced count after task work
        :param work_task_id:
        :param hashlist_id:
        :return:
        """
        self._db.q(
            "UPDATE task_works SET uncracked_after = "
            "(SELECT COUNT(id) FROM hashes WHERE hashlist_id = {0} AND !cracked) "
            "WHERE id = {1}".format(hashlist_id, work_task_id)
        )

    def run(self):
        """ Run thread """
        while self.available:
            if self.get_waiting_task_for_work():
                Registry().get('logger').log("result_parser", "Getted result of task #{0}".format(self.get_current_work_task_id()))
                self.update_status("outparsing")

                work_task = self.get_work_task_data()
                hashlist = self.get_hashlist_data(work_task['hashlist_id'])

                if len(work_task['out_file']) and os.path.exists(work_task['out_file']):
                    Registry().get('logger').log("result_parser", "Start put found passwords info DB")

                    self.parse_outfile_and_fill_found_hashes(work_task, hashlist)

                    self.update_status('done')

                    #os.remove(work_task['out_file'])
                    #self._update_work_task_field('out_file', '')

                    self.update_task_uncracked_count(work_task['id'], work_task['hashlist_id'])

                    self.update_all_hashlists_counts_by_alg_id(hashlist['alg_id'])
                else:
                    self.update_status('done')
                    Registry().get('logger').log("result_parser", "Outfile {0} not exists".format(work_task['out_file']))

                    Registry().get('logger').log("result_parser", "Work for task #{0} done".format(self.get_current_work_task_id()))

            time.sleep(self.delay_per_check)
