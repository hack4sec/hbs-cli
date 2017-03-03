# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Parent for all threads
"""
import threading
import traceback

from classes.Registry import Registry

class CommonThread(threading.Thread):
    """ Parent for all threads """
    available = True

    daemon = True

    died_by_exception = False
    exception_str = ""
    catch_exceptions = True

    thread_name = ""

    def __init__(self):
        threading.Thread.__init__(self)

    def exception(self, ex):
        """
        Turn off thread, log information about exception. If self,catch_exceptions property is false,
        raise exception through (need for test)
        :param ex: Exception object
        :return:
        """
        if self.catch_exceptions is False:
            raise ex

        self.available = False
        self.died_by_exception = True
        self.exception_str = traceback.format_exc()
        self.log("Died by exception:\n{0}".format(self.exception_str))

    def log(self, msg):
        """
        Put message for logger
        :param msg:
        :return:
        """
        Registry().get('logger').log(self.thread_name, msg)