# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Thread for load hashlists
"""

import time
import os
import subprocess
import shutil

from classes.Registry import Registry
from classes.Factory import Factory
from classes.HbsException import HbsException
from classes.CommonThread import CommonThread
from libs.common import file_lines_count, gen_random_md5, md5, update_hashlist_counts


class HashlistsLoaderThread(CommonThread):
    """ Thread for load hashlists """
    current_hashlist_id = None
    delay_per_check = None
    thread_name = "hashlist_loader"

    def __init__(self):
        """ Initialization """
        CommonThread.__init__(self)
        config = Registry().get('config')

        self.tmp_dir = config['main']['tmp_dir']
        self.dicts_path = config['main']['dicts_path']
        self.outs_path = config['main']['outs_path']
        self.rules_path = config['main']['rules_path']
        self.path_to_hc = config['main']['path_to_hc']
        self.hc_bin = config['main']['hc_bin']
        self.delay_per_check = int(config['main']['hashlists_loader_delay_per_try'])

        self._db = Factory().new_db_connect()

    def get_current_hashlist_id(self):
        """
        Get current hashlist id of exception if it not set
        :exception HbsException:
        :return int:
        """
        if self.current_hashlist_id is None:
            raise HbsException("Current hashlist not set")
        return self.current_hashlist_id

    def update_status(self, status):
        """
        Update hashlist status
        :param status:
        :return:
        """
        self.update_hashlist_field('status', status)

    def get_current_hashlist_data(self):
        """
        Get row data of current hashlist
        :return dict:
        """
        return self._db.fetch_row("SELECT * FROM hashlists WHERE id = {0}".format(self.get_current_hashlist_id()))

    def parsed_flag(self, parsed):
        """
        Set flag 'parsed' to current hashlist
        :param parsed:
        :return:
        """
        self.update_hashlist_field('parsed', parsed)

    def update_hashlist_field(self, field, value):
        """
        Update one hashlist field
        :param field:
        :param value:
        :return:
        """
        self._db.update("hashlists", {field: value}, "id = {0}".format(self.get_current_hashlist_id()))

    def sort_file(self, hashlist):
        """
        Sort hashlist`s txt file with duplicates delete
        :param hashlist: hashlists row
        :return:
        """
        self.update_status("sorting")

        sorted_path = self.tmp_dir + "/" + gen_random_md5()
        subprocess.check_output(
            "sort -u {0} > {1}".format(hashlist['tmp_path'], sorted_path),
            shell=True
        )
        self.log("Before sort - {0}, after - {1}".format(file_lines_count(hashlist['tmp_path']),
                                                                              file_lines_count(sorted_path)))
        return sorted_path

    def sorted_file_to_db_file(self, sorted_file_path, hashlist):
        """
        Convert sorted txt hashlist to in-db file
        :param sorted_file_path:
        :param hashlist: hashlist data
        :return:
        """
        self.update_status("preparedb")
        self.log("Prepare file for DB load")

        errors_lines = ""

        put_in_db_path = self.tmp_dir + "/" + gen_random_md5()
        fh_to_db = open(put_in_db_path, 'w')

        fh_sorted = open(sorted_file_path)
        for _line in fh_sorted:
            _hash = None
            _line = _line.strip()
            if int(hashlist['have_salts']):
                if _line.count(hashlist['delimiter']):
                    _hash = _line[:_line.index(hashlist['delimiter'])]
                    salt = _line[_line.index(hashlist['delimiter']) + len(hashlist['delimiter']):]
                else:
                    errors_lines += _line + "\n"
            else:
                _hash = _line
                salt = ""

            if _hash is not None:
                fh_to_db.write(
                    '"{0}","{1}","{2}","{3}"\n'.format(
                        hashlist['id'],
                        _hash.replace('\\', '\\\\').replace('"', '\\"'),
                        salt.replace('\\', '\\\\').replace('"', '\\"'),
                        md5(_hash + ":" + salt) if len(salt) else md5(_hash)
                    )
                )

        fh_to_db.close()
        fh_sorted.close()

        os.remove(sorted_file_path)

        if len(errors_lines):
            self.update_hashlist_field("errors", errors_lines)

        return put_in_db_path

    def load_file_in_db(self, file_path):
        """
        Import in-db file in database with mysqlimport util
        :param file_path:
        :return:
        """
        self.update_status('putindb')
        self.log("Data go to DB")

        if os.path.exists(self.tmp_dir + "/hashes"):
            os.remove(self.tmp_dir + "/hashes")

        hashes_file_path = self.tmp_dir + "/hashes"
        shutil.move(file_path, hashes_file_path)

        importcmd = "mysqlimport --lock-tables --user {0} -p{1} --local " \
                    "--columns hashlist_id,hash,salt,summ --fields-enclosed-by '\"'" \
                    " --fields-terminated-by ',' --fields-escaped-by \"\\\\\" {2} {3}"\
                    .format(
                        Registry().get('config')['main']['mysql_user'],
                        Registry().get('config')['main']['mysql_pass'],
                        Registry().get('config')['main']['mysql_dbname'],
                        self.tmp_dir + "/hashes"
                    )

        subprocess.check_output(importcmd, shell=True)

        os.remove(hashes_file_path)

    def find_similar_found_hashes(self, hashlist):
        """
        Get all cracked hashes of same alg and search them in current hashlist
        :param hashlist: hashlist data
        :return:
        """
        self.update_status('searchfound')
        self.log("Search already found hashes")

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

    def get_hashlist_for_load(self):
        """
        Are we have hashlist ready to parse?
        :return int: hashlist id
        """
        self.current_hashlist_id = self._db.fetch_one(
            "SELECT id FROM hashlists WHERE parsed = 0 AND status='wait' ORDER BY id ASC LIMIT 1")
        return self.current_hashlist_id

    def run(self):
        """ Run thread """
        try:
            while self.available:
                if self.get_hashlist_for_load():
                    self.update_status("parsing")

                    hashlist = self.get_current_hashlist_data()

                    self.log("Found hashlist #{0}/{1} for work".format(
                        self.current_hashlist_id, hashlist['name']))
                    if not len(hashlist['tmp_path']) or not os.path.exists(hashlist['tmp_path']):
                        self.log("ERR: path not exists #{0}/'{1}'".format(
                            self.current_hashlist_id, hashlist['tmp_path']))

                        self.update_status("errpath")
                        self.parsed_flag(1)
                        continue

                    sorted_path = self.sort_file(hashlist)

                    put_in_db_path = self.sorted_file_to_db_file(sorted_path, hashlist)

                    self.load_file_in_db(put_in_db_path)

                    self.find_similar_found_hashes(hashlist)

                    update_hashlist_counts(self._db, hashlist['id'])

                    self.parsed_flag(1)
                    self.update_status('ready')
                    self.update_hashlist_field('tmp_path', '')
                    os.remove(hashlist['tmp_path'])

                    self.log("Work for hashlist {0}/{1} done".format(
                        self.current_hashlist_id, hashlist['name']))

                time.sleep(self.delay_per_check)
        except BaseException as ex:
            self.exception(ex)
