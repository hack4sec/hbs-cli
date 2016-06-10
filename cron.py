#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Main cron of HBS """

import sys
import time
import os

import configparser

from classes.Database import Database
from classes.Registry import Registry
from classes.WorkerThrd import WorkerThrd

config = configparser.ConfigParser()
config.read(os.getcwd() + '/' + 'config.ini')
Registry().set('config', config)

db = Database(
    config['main']['mysql_host'],
    config['main']['mysql_user'],
    config['main']['mysql_pass'],
    config['main']['mysql_dbname']
)

if not os.path.exists(config['main']['tmp_dir']):
    print "ERROR: Tmp path {0} is not exists!".format(config['main']['tmp_dir'])
    exit(0)

if not os.access(config['main']['tmp_dir'], os.W_OK):
    print "ERROR: Tmp path {0} is not writable!".format(config['main']['tmp_dir'])
    exit(0)

if not os.path.exists(config['main']['outs_path']):
    print "ERROR: Outs path {0} is not exists!".format(config['main']['outs_path'])
    exit(0)

if not os.access(config['main']['outs_path'], os.W_OK):
    print "ERROR: Outs path {0} is not writable!".format(config['main']['outs_path'])
    exit(0)

if not os.path.exists(config['main']['dicts_path']):
    print "ERROR: Dicts path {0} is not exists!".format(config['main']['dicts_path'])
    exit(0)

if not os.access(config['main']['dicts_path'], os.W_OK):
    print "ERROR: Dicts path {0} is not writable!".format(config['main']['dicts_path'])
    exit(0)

if not os.path.exists(config['main']['path_to_hc']):
    print "ERROR: HC path {0} is not exists!".format(config['main']['path_to_hc'])
    exit(0)

if not os.path.exists("{0}/{1}".format(config['main']['path_to_hc'], config['main']['hc_bin'])):
    print "ERROR: HC bin {0}/{1} is not exists!".format(config['main']['path_to_hc'], config['main']['hc_bin'])
    exit(0)

print "Started at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
sys.stdout.flush()

Registry().set('db', db)

work_thrd = None
while True:
    next_work_task = db.fetch_row("SELECT * FROM task_works WHERE status='wait' ORDER BY priority DESC LIMIT 1")
    if next_work_task:
        work_thrd = WorkerThrd(next_work_task)
        work_thrd.setDaemon(True)
        work_thrd.start()

        while not work_thrd.done:
            time.sleep(3)

        del work_thrd
        work_thrd = None
    else:
        pass

    time.sleep(5)


