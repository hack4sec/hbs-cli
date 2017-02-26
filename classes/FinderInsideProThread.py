# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Thread for automated check hashes on finder.insidepro.com
"""

import threading
import time

from classes.Registry import Registry
from classes.Factory import Factory
from classes.FinderInsidePro import FinderInsidePro, FinderInsideProException
from libs.common import _d, gen_random_md5, md5

class FinderInsideProThread(threading.Thread):
    """ Thread for automated check hashes on finder.insidepro.com """
    daemon = True
    available = True
    time_for_check = 3600*24*7
    delay_per_check = None
    UNIQUE_DELIMITER = 'UNIQUEDELIMITER'

    def __init__(self):
        threading.Thread.__init__(self)
        config = Registry().get('config')

        self.tmp_dir = config['main']['tmp_dir']
        self.finder_key = config['main']['finder_key']
        self.delay_per_check = int(config['main']['finder_insidepro_delay_per_try'])

        self._db = Factory().new_db_connect()

        self.finder = FinderInsidePro(config['main']['finder_key'])

    def is_alg_in_parse(self, alg_id):
        """
        Check is current alg now in parse or wait parse (work tasks with this alg)
        :param alg_id:
        :return bool:
        """
        result = self._db.fetch_one(
            "SELECT t.id FROM `task_works` t, `hashlists` hl "
            "WHERE t.hashlist_id = hl.id AND hl.alg_id = {0} "
            "AND t.status IN('waitoutparse','outparsing')".format(alg_id)
        )
        return bool(result)

    def get_ready_common_hashlists(self):
        """
         Return lists of common hashlists ready for Finder work
        :return list: List of hashes row
        """
        return self._db.fetch_all(
            "SELECT hl.* FROM hashlists hl, algs a "
            "WHERE a.id = hl.alg_id AND hl.common_by_alg <> 0 AND hl.status = 'ready' "
            "AND a.finder_insidepro_allowed = 1 AND hl.last_finder_checked + {0} < {1}".format(
                self.time_for_check, int(time.time())
            )
        )

    def make_hashlist(self, hashlist_id):
        """
        Build text file with uncracked hashes by hashlist id
        :param hashlist_id:
        :return str: Path of text file
        """
        path_to_hashlist = self.tmp_dir + "/" + gen_random_md5()
        fh = open(path_to_hashlist, 'w')

        res = self._db.q(
            ("SELECT IF(LENGTH(salt), CONCAT(`hash`, '{1}', salt), hash) as hash "
             "FROM `hashes` WHERE hashlist_id={0} AND cracked = 0")
            .format(
                hashlist_id,
                self.UNIQUE_DELIMITER
            )
        )
        for _hash in res:
            fh.write(_hash[0] + "\n")
        fh.close()

        return path_to_hashlist

    def put_found_hashes_in_db(self, alg_id, hashes):
        """
        Put found by Finder hashes in db
        :param alg_id:
        :param hashes: list of found hashes
        :return:
        """
        for _hash in hashes:
            summ = md5("{0}:{1}".format(_hash['hash'], _hash['salt'])) if len(_hash['salt']) else md5(_hash['hash'])

            self._db.q(
                "UPDATE `hashes` h, hashlists hl "
                "SET h.`password` = {0}, h.cracked = 1 "
                "WHERE h.hashlist_id = hl.id AND hl.alg_id = {1} AND h.summ = {2} AND h.cracked = 0"
                .format(
                    self._db.quote(_hash['password']),
                    alg_id,
                    self._db.quote(summ),
                )
            )

    def run(self):
        """ Run thread """
        while self.available:
            hashlists = self.get_ready_common_hashlists()
            for hashlist in hashlists:
                found_count = 0
                all_count = 0
                if self.is_alg_in_parse(hashlist['alg_id']):
                    continue

                hc_alg_id = self._db.fetch_one("SELECT alg_id FROM algs WHERE id = {0}".format(hashlist['alg_id']))

                path_to_hashlist_file = self.make_hashlist(hashlist['id'])

                hashes_to_finder = []
                fh = open(path_to_hashlist_file, 'r')
                for line in fh:
                    if line.count(self.UNIQUE_DELIMITER):
                        _hash, _salt = line.strip().split(self.UNIQUE_DELIMITER)
                    else:
                        _hash = line.strip()
                        _salt = ''
                    hashes_to_finder.append({'hash': _hash, 'salt': _salt})

                    if not len(hashes_to_finder) % FinderInsidePro.hashes_per_once_limit:
                        all_count += len(hashes_to_finder)

                        try:
                            found_hashes = self.finder.search_hashes(hashes_to_finder, hc_alg_id)
                        except FinderInsideProException as ex:
                            if ex.extype == FinderInsideProException.TYPE_SMALL_REMAIN:
                                _d("finderinsidepro", str(ex))
                                break
                            else:
                                raise ex

                        found_count += len(found_hashes)

                        self.put_found_hashes_in_db(hashlist['alg_id'], found_hashes)
                        hashes_to_finder = []

                if len(hashes_to_finder):
                    all_count += len(hashes_to_finder)
                    try:
                        found_hashes = self.finder.search_hashes(hashes_to_finder, hc_alg_id)
                    except FinderInsideProException as ex:
                        if ex.extype == FinderInsideProException.TYPE_SMALL_REMAIN:
                            _d("finderinsidepro", str(ex))
                            break
                        else:
                            raise ex
                    found_count += len(found_hashes)
                    self.put_found_hashes_in_db(hashlist['alg_id'], found_hashes)

                _d("finderinsidepro", "For hashlist {0} with alg {1} found {2} from {3}".format(
                    hashlist['id'], hashlist['alg_id'], found_count, all_count
                ))

                self._db.update("hashlists", {"last_finder_checked": int(time.time())}, "id = " + str(hashlist['id']))

                fh.close()

            time.sleep(self.delay_per_check)
