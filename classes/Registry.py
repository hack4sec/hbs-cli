"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)
"""

class Registry:
    data = {}
    def get(self, key):
        return Registry.data[key]
    def set(self, key, value):
        Registry.data[key] = value
    def isset(self, key):
        return key in Registry.data