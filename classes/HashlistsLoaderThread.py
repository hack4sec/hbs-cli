# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Thread for load hashlists
"""

import threading
import time
import os
import subprocess
import shutil

from subprocess import Popen, PIPE, check_output
from classes.Registry import Registry
from classes.Factory import Factory
from libs.common import _d, file_lines_count, gen_random_md5, md5, update_hashlist_counts
from classes.Database import Database
from classes.HbsException import HbsException


class HashlistsLoaderThread(threading.Thread):
    _current_hashlist_id = None
    daemon = True
    _sleep_time = 60

    def __init__(self):
        threading.Thread.__init__(self)
        config = Registry().get('config')

        self.tmp_dir = config['main']['tmp_dir']
        self.dicts_path = config['main']['dicts_path']
        self.outs_path = config['main']['outs_path']
        self.rules_path = config['main']['rules_path']
        self.path_to_hc = config['main']['path_to_hc']
        self.hc_bin = config['main']['hc_bin']

        self._db = Factory().new_db_connect()

    def get_current_hashlist_id(self):
        if self._current_hashlist_id is None:
            raise HbsException("Current hashlist not set")
        return self._current_hashlist_id

    def _update_status(self, status):
        self._update_hashlist_field('status', status)

    def _get_current_hashlist_data(self):
        return self._db.fetch_row("SELECT * FROM hashlists WHERE id = {0}".format(self.get_current_hashlist_id()))

    def _parsed_flag(self, parsed):
        self._update_hashlist_field('parsed', parsed)

    def _update_hashlist_field(self, field, value):
        self._db.update("hashlists", {field: value}, "id = {0}".format(self.get_current_hashlist_id()))

    def _sort_file(self, hashlist):
        self._update_status("sorting")

        sorted_path = self.tmp_dir + "/" + gen_random_md5()
        subprocess.check_output(
            "sort -u {0} > {1}".format(hashlist['tmp_path'], sorted_path),
            shell=True
        )
        _d("hashlist_loader", "Before sort - {0}, after - {1}".format(file_lines_count(hashlist['tmp_path']),
                                                                      file_lines_count(sorted_path)))
        return sorted_path

    def _sorted_file_to_db_file(self, sorted_file_path, hashlist):
        self._update_status("preparedb")
        _d("hashlist_loader", "Prepare file for DB load")

        errors_lines = ""

        put_in_db_path = self.tmp_dir + "/" + gen_random_md5()
        fh_to_db = open(put_in_db_path, 'w')

        fh_sorted = open(sorted_file_path)
        for _line in fh_sorted:
            hash = None
            _line = _line.strip()
            if int(hashlist['have_salts']):
                if _line.count(hashlist['delimiter']):
                    hash = _line[:_line.index(hashlist['delimiter'])]
                    salt = _line[_line.index(hashlist['delimiter']) + len(hashlist['delimiter']):]
                else:
                    errors_lines += _line + "\n"
            else:
                hash = _line
                salt = ""

            if hash is not None:
                fh_to_db.write(
                    '"{0}","{1}","{2}","{3}"\n'.format(
                        hashlist['id'],
                        hash.replace('\\', '\\\\').replace('"', '\\"'),
                        salt.replace('\\', '\\\\').replace('"', '\\"'),
                        md5(hash + ":" + salt) if len(salt) else md5(hash)
                    )
                )

        fh_to_db.close()
        fh_sorted.close()

        os.remove(sorted_file_path)

        if len(errors_lines):
            self._update_hashlist_field("errors", errors_lines)

        return put_in_db_path

    def _load_file_in_db(self, file_path, hashlist):
        self._update_status('putindb')
        _d("hashlist_loader", "Data go to DB")

        if os.path.exists(self.tmp_dir + "/hashes"):
            os.remove(self.tmp_dir + "/hashes")

        hashes_file_path = self.tmp_dir + "/hashes"
        shutil.move(file_path, hashes_file_path)

        importcmd = "mysqlimport --lock-tables --user {0} -p{1} --local --columns hashlist_id,hash,salt,summ --fields-enclosed-by '\"'" \
        " --fields-terminated-by ',' --fields-escaped-by \"\\\\\" {2} {3}"\
            .format(
            Registry().get('config')['main']['mysql_user'],
            Registry().get('config')['main']['mysql_pass'],
            Registry().get('config')['main']['mysql_dbname'],
            self.tmp_dir + "/hashes"
        )

        subprocess.check_output(importcmd, shell=True)

        os.remove(hashes_file_path)
        os.remove(hashlist['tmp_path'])

    def _find_similar_found_hashes(self, hashlist):
        self._update_status('searchfound')
        _d("hashlist_loader", "Search already found hashes")

        similar_hashes = self._db.fetch_all(
            "SELECT hash, salt, password, summ FROM `hashes` h, hashlists hl "
            "WHERE h.hashlist_id = hl.id AND hl.alg_id = {0} AND h.cracked = 1 GROUP BY `summ`".format(
                hashlist['alg_id'])
        )
        for similar_hash in similar_hashes:
            hash_id = self._db.fetch_one(
                "SELECT id FROM hashes WHERE hashlist_id = {0} "
                "AND !cracked AND summ = '{1}'".format(hashlist['id'], similar_hash['summ'])
            )
            if hash_id:
                self._db.update(
                    "hashes",
                    {
                        'cracked': '1',
                        'password': similar_hash['password'].encode('utf8')
                    },
                    "id = " + str(hash_id)
                )

    def _get_hashlist_for_load(self):
        self._current_hashlist_id = self._db.fetch_one("SELECT id FROM hashlists WHERE parsed = 0 AND status='wait' ORDER BY id ASC LIMIT 1")
        return self._current_hashlist_id

    def run(self):
        while True:
            if self._get_hashlist_for_load():
                self._update_status("parsing")

                hashlist = self._get_current_hashlist_data()

                _d("hashlist_loader", "Found hashlist #{0}/{1} for work".format(self._current_hashlist_id, hashlist['name']))
                if not len(hashlist['tmp_path']) or not os.path.exists(hashlist['tmp_path']):
                    _d("hashlist_loader", "ERR: path not exists #{0}/'{1}'".format(self._current_hashlist_id, hashlist['tmp_path']))
                    self._update_status("errpath")
                    self._parsed_flag(1)
                    continue

                sorted_path = self._sort_file(hashlist)

                put_in_db_path = self._sorted_file_to_db_file(sorted_path, hashlist)

                self._load_file_in_db(put_in_db_path, hashlist)

                self._find_similar_found_hashes(hashlist)

                update_hashlist_counts(self._db, hashlist['id'])

                self._parsed_flag(1)
                self._update_status('ready')
                self._update_hashlist_field('tmp_path', '')

                _d("hashlist_loader", "Work for hashlist {0}/{1} done".format(self._current_hashlist_id, hashlist['name']))

            time.sleep(self._sleep_time)
        pass


