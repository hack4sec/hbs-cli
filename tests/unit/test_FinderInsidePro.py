# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Unit tests for FinderInsidePro API class
"""

import sys
import pytest

sys.path.append('../../')

from classes.Registry import Registry
from classes.FinderInsidePro import FinderInsidePro, FinderInsideProException
from CommonUnit import CommonUnit


class Test_FinderInsidePro(CommonUnit):
    """ Unit tests for FinderInsidePro API class """
    test_key = ''

    def setup(self):
        """ Tests setup """
        self.test_key = Registry().get('config')['main']['finder_key']

    def test_wrong_key(self):
        """ Test on exception with blank or wrong key set """
        with pytest.raises(FinderInsideProException) as ex:
            FinderInsidePro("")
        assert FinderInsideProException.EXCEPTION_TEXT_KEY_NOT_SET in str(ex)
        assert ex.value.extype == FinderInsideProException.TYPE_KEY_IS_WRONG

        with pytest.raises(FinderInsideProException) as ex:
            FinderInsidePro('aaa')
        assert FinderInsideProException.EXCEPTION_TEXT_WRONG_KEY in str(ex)
        assert ex.value.extype == FinderInsideProException.TYPE_KEY_IS_WRONG

    def test_get_remain_limit(self):
        """ Test on get remain limit from server """
        finder = FinderInsidePro(self.test_key)
        limit = finder.get_remain_limit()
        assert isinstance(limit, int)
        assert limit > 0

    def test_create_session(self):
        """ Test on session create """
        finder = FinderInsidePro(self.test_key)
        session_id = finder.create_session()
        assert isinstance(session_id, str)
        assert session_id == finder.session_id
        assert len(session_id)

    test_data = [(True,), (False,)]

    def test_search_hashes(self):
        """ Test on hashes search. 2 hashes - 1 found, 1 not """
        finder = FinderInsidePro(self.test_key)

        test_hashes = []
        for _ in range(0, 1010):
            test_hashes.append(1)
        with pytest.raises(FinderInsideProException) as ex:
            finder.search_hashes(test_hashes)
        assert FinderInsideProException.EXCEPTION_TEXT_HASHES_COUNT_LIMIT.format(
            FinderInsidePro.hashes_per_once_limit) in str(ex)
        assert ex.value.extype is None

        hashes = [
            {'hash': '0065ffe5f9e4e5996c2c3f52f81c6e31', 'salt': 'cB6Ar'},
            {'hash': '20e153b046072c949562f3c939611db8', 'salt': '0RTV'},
        ]
        test_data = [{'hash': '0065ffe5f9e4e5996c2c3f52f81c6e31', 'salt': 'cB6Ar', 'password': 'y0007171'},]

        assert test_data == finder.search_hashes(hashes)

        finder.session_id = 'WRONG'
        assert test_data == finder.search_hashes(hashes)

    def test_parse_and_fill_hashes_from_xml(self):
        """ Test by xml-response from finder parsing method """
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>' \
                  '<d>' \
                  '<i><a>16</a><r>1</r><h>0065ffe5f9e4e5996c2c3f52f81c6e31</h><p>y0007171</p></i>' \
                  '<i><r>0</r><s>20e153b046072c949562f3c939611db8:0RTV</s></i>' \
                  '</d>'
        hashes = [
            {'hash': '0065ffe5f9e4e5996c2c3f52f81c6e31', 'salt': 'cB6Ar'},
            {'hash': '20e153b046072c949562f3c939611db8', 'salt': '0RTV'},
        ]
        test_data = [{'hash': '0065ffe5f9e4e5996c2c3f52f81c6e31', 'salt': 'cB6Ar', 'password': 'y0007171'},]

        finder = FinderInsidePro(self.test_key)
        assert test_data == finder.parse_and_fill_hashes_from_xml(xml_str, hashes)
