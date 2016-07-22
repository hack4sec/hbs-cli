# -*- coding: utf-8 -*-
""" Work thread """

import threading
import time
import os
import subprocess

from subprocess import Popen, PIPE, check_output
from classes.Registry import Registry
from classes.Factory import Factory
from libs.common import _d, file_lines_count, gen_random_md5, md5
from classes.Database import Database


class HashlistsLoaderThread(threading.Thread):
    current_hashlist_id = None
    daemon = True

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

    def _update_status(self, status):
        self._update_hashlist_field('status', status)

    def _get_hashlist_data(self):
        return self._db.fetch_row("SELECT * FROM hashlists WHERE id = {0}".format(self.current_hashlist_id))

    def _parsed_flag(self, parsed):
        self._update_hashlist_field('parsed', parsed)

    def _update_hashlist_field(self, field, value):
        self._db.update("hashlists", {field: value}, "id = {0}".format(self.current_hashlist_id))

    def run(self):
        while True:
            self.current_hashlist_id = self._db.fetch_one("SELECT id FROM hashlists WHERE parsed = 0 ORDER BY id ASC LIMIT 1")
            if self.current_hashlist_id:
                self._update_status("parsing")

                errors_lines = ""

                hashlist = self._get_hashlist_data()
                _d("hashlist_loader", "Found hashlist #{0}/{1} for work".format(self.current_hashlist_id, hashlist['name']))
                if len(hashlist['tmp_path']) and os.path.exists(hashlist['tmp_path']):
                    self._update_status("sorting")

                    lines_count_before_sort = file_lines_count(hashlist['tmp_path'])
                    sorted_path = self.tmp_dir + "/" + gen_random_md5()
                    subprocess.check_output(
                        "sort -u {0} > {1}".format(hashlist['tmp_path'], sorted_path),
                        shell=True
                    )
                    lines_count_after_sort = file_lines_count(sorted_path)
                    _d("hashlist_loader", "Before sort - {0}, after - {1}".format(lines_count_before_sort, lines_count_after_sort))

                    self._update_status("preparedb")
                    _d("hashlist_loader", "Prepare file for DB load")

                    put_in_db_path = self.tmp_dir + "/" + gen_random_md5()
                    fh_to_db = open(put_in_db_path, 'w')

                    fh_sorted = open(sorted_path)
                    for _line in fh_sorted:
                        _line = _line.strip()
                        if int(hashlist['have_salts']):
                            if _line.count(hashlist['delimiter']):
                                hash = _line[:_line.index(hashlist['delimiter'])]
                                salt = _line[_line.index(hashlist['delimiter'])+1:]
                            else:
                                errors_lines += _line + "\n"
                        else:
                            hash = _line
                            salt = ""

                        fh_to_db.write(
                            '"{0}","{1}","{2}","{3}"\n'.format(
                                hashlist['id'],
                                hash.replace('"', '\\"'),
                                salt.replace('"', '\\"'),
                                md5(hash + ":" + salt) if len(salt) else md5(hash)
                            )
                        )

                    fh_to_db.close()
                    fh_sorted.close()

                    if len(errors_lines):
                        self._update_hashlist_field("errors", errors_lines)
                        del errors_lines

                    self._update_status('putindb')
                    _d("hashlist_loader", "Data go to DB")

                    self._db.q(
                        "LOAD DATA LOCAL INFILE '{0}' INTO TABLE `hashes` "
                        "FIELDS TERMINATED BY ',' ENCLOSED BY '\"' "
                        "ESCAPED BY '\\\\' "
                        "(hashlist_id, hash, salt, summ)".format(
                            put_in_db_path
                        )
                    )

                    os.remove(put_in_db_path)
                    os.remove(sorted_path)
                    os.remove(hashlist['tmp_path'])

                    self._update_status('searchfound')
                    _d("hashlist_loader", "Search already found hashes")

                    similar_hashes = self._db.fetch_all(
                        "SELECT hash, salt, password, summ FROM `hashes` h, hashlists hl "
                        "WHERE h.hashlist_id = hl.id AND hl.alg_id = {0} AND h.cracked = 1 GROUP BY `summ`".format(hashlist['alg_id'])
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
                                    'password': similar_hash['password']
                                },
                                "id = " + str(hash_id)
                            )



                    self._parsed_flag(1)
                    self._update_status('ready')

                    self._update_hashlist_field('tmp_path', '')
                else:
                    self._update_status("errpath")
                    self._parsed_flag(1)

                _d("hashlist_loader", "Work for hashlist {0}/{1} done".format(self.current_hashlist_id, hashlist['name']))


            self.current_hashlist_id = None
            time.sleep(60)
        pass


