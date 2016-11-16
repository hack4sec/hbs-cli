# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Thread for compile hashlists by common (one) alg
"""

import threading
import time

from classes.Registry import Registry
from classes.Factory import Factory
from libs.common import _d, gen_random_md5, file_put_contents


class HashlistsByAlgLoaderThread(threading.Thread):
    """ Thread for compile hashlists by common (one) alg """
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

    def _hashlist_by_alg_exists(self, alg_id):
        return self._db.fetch_one("SELECT id FROM hashlists WHERE common_by_alg = {0}".format(alg_id))

    def _get_current_work_hashlist(self):
        return self._db.fetch_one("SELECT hashlist_id FROM task_works WHERE status='work'")

    def _get_hashlist_status(self, hashlist_id):
        return self._db.fetch_one("SELECT status FROM hashlists WHERE id = {0}".format(hashlist_id))

    def _hashes_count_in_hashlist(self, hashlist_id):
        return self._db.fetch_one("SELECT COUNT(id) FROM hashes WHERE hashlist_id = {0}".format(hashlist_id))

    def run(self):
        while True:
            hashes_by_algs_count = self._db.fetch_pairs(
                "SELECT hl.alg_id, COUNT(DISTINCT h.hash) FROM `hashes` h, hashlists hl "
                "WHERE h.hashlist_id = hl.id AND !h.cracked AND hl.common_by_alg = 0 GROUP BY hl.alg_id"
            )

            for alg_id in hashes_by_algs_count:
                hashlist_id = self._hashlist_by_alg_exists(alg_id)

                hashes_count_in_hashlist = self._hashes_count_in_hashlist(hashlist_id) if hashlist_id else 0
                alg_have_salts = self._db.fetch_one(
                    "SELECT have_salts FROM hashlists WHERE alg_id = {0} LIMIT 1".format(alg_id)
                )

                if hashes_count_in_hashlist != hashes_by_algs_count[alg_id]:
                    _d(
                        "hashlist_common_loader",
                        "Build list for alg #{0} ({1} vs {2})".format(
                            alg_id,
                            hashes_count_in_hashlist,
                            hashes_by_algs_count[alg_id]
                        )
                    )

                    if hashlist_id:
                        if hashlist_id == self._get_current_work_hashlist() or \
                            self._get_hashlist_status(hashlist_id) != 'ready':
                            _d(
                                "hashlist_common_loader",
                                "Skip it, it in work or not ready #{0}/{1}/{2}".format(
                                    hashlist_id,
                                    self._get_current_work_hashlist(),
                                    self._get_hashlist_status(hashlist_id)
                                )
                            )
                            continue

                        # Mark as 'parsing' for HashlistsLoader don`t get it to work before we done
                        self._db.update("hashlists", {'parsed': 0, 'status': 'parsing'}, "id = {0}".format(hashlist_id))

                    curs = self._db.q(
                        "SELECT CONCAT(h.hash, 'UNIQUEDELIMITER', h.salt) as hash FROM hashes h, hashlists hl "
                        "WHERE hl.id = h.hashlist_id AND hl.alg_id = {0} AND hl.common_by_alg = 0 AND !h.cracked".format(alg_id)
                        if alg_have_salts else
                        "SELECT h.hash FROM hashes h, hashlists hl "
                        "WHERE hl.id = h.hashlist_id AND hl.alg_id = {0} AND hl.common_by_alg = 0 AND !h.cracked".format(alg_id)
                    )

                    if hashlist_id:
                        _d("hashlist_common_loader", "Delete old hashes of #{0}".format(hashlist_id))
                        self._db.q("DELETE FROM hashes WHERE hashlist_id = {0}".format(hashlist_id))
                        self._db.q("UPDATE hashlists SET cracked=0, uncracked=0 WHERE id = {0}".format(hashlist_id))

                    _d("hashlist_common_loader", "Put data in file for #{0}".format(hashlist_id))
                    tmp_path = self.tmp_dir + "/" + gen_random_md5()
                    for row in curs:
                        file_put_contents(tmp_path, "{0}\n".format(row[0].strip()), True)

                    if not hashlist_id:
                        alg_name = self._db.fetch_one("SELECT name FROM algs WHERE id = {0}".format(alg_id))
                        hashlist_id = self._db.insert(
                            "hashlists",
                            {
                                'name': 'All-{0}'.format(alg_name),
                                'alg_id': alg_id,
                                'have_salts': alg_have_salts,
                                'delimiter': 'UNIQUEDELIMITER',
                                'parsed': '0',
                                'tmp_path': tmp_path,
                                'status': 'wait',
                                'when_loaded': '0',
                                'common_by_alg': alg_id,
                            }
                        )
                    else:
                        self._db.update(
                            "hashlists",
                            {
                                'parsed': '0',
                                'status': 'wait',
                                'tmp_path': tmp_path
                            },
                            "id = {0}".format(hashlist_id)
                        )
                    _d("hashlist_common_loader", "Done #{0}".format(hashlist_id))

            time.sleep(60)
