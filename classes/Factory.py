"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)
"""
from classes.Database import Database
from classes.Registry import Registry


class Factory:
    def new_db_connect(self):
        """ Function return new mysql connection (for multiple usage in threads) """
        config = Registry().get('config')
        return Database(
            config['main']['mysql_host'],
            config['main']['mysql_user'],
            config['main']['mysql_pass'],
            config['main']['mysql_dbname']
        )