# -*- coding: utf-8 -*-
"""
This is part of HashBruteStation software
Docs EN: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station_en
Docs RU: http://hack4sec.pro/wiki/index.php/Hash_Brute_Station
License: MIT
Copyright (c) Anton Kuzmin <http://anton-kuzmin.ru> (ru) <http://anton-kuzmin.pro> (en)

Api for finder.insidepro.com
"""

import urllib

import requests
from lxml import etree


class FinderInsideProException(Exception):
    """ Exeptions class for finder.insidepro.com API """
    TYPE_SESSION_IS_WRONG = "0"
    TYPE_KEY_IS_WRONG = "1"
    TYPE_SMALL_REMAIN = "2"

    EXCEPTION_TEXT_WRONG_KEY = "Check key valid, server answer 403"
    EXCEPTION_TEXT_KEY_NOT_SET = "Finder key is not set"
    EXCEPTION_TEXT_HASHES_COUNT_LIMIT = "Hashes count must be less {0}"
    EXCEPTION_TEXT_SMALL_REMAIN = "Count of remain hashes ({0}) less when limit ({1})"

    SESSION_ERROR_TEXT = "Session not initialized"

    REQUEST_ERROR_TEXT = "Unknown error in response. Code: '{0}', text: '{1}'"

    extype = None

    def __init__(self, msg, extype=None):
        super(FinderInsideProException, self).__init__(msg)
        self.extype = extype


class FinderInsidePro(object):
    """ Class with API for finder.insidepro.com """
    key = ''
    session_id = ''

    hashes_per_once_limit = 1000

    def __init__(self, key):
        """
        Initialization
        :param key: Key for finder.insidepro.com software client
        """
        if not key:
            raise FinderInsideProException(
                FinderInsideProException.EXCEPTION_TEXT_KEY_NOT_SET, FinderInsideProException.TYPE_KEY_IS_WRONG)
        self.key = key

        self.get_remain_limit()

    def get_xml_from_server(self, url, post_data=False):
        """
        Method get xml response from server and check validaty of it. Accept POST and GET methods.
        If you give post_data, request will be POST, else GET.
        :exception FinderInsideProException: If response code will be 403 (key invalid)
        :exception FinderInsideProException: If response code will be 400 + session broken message
        :exception FinderInsideProException: Other cases with non-200 response code
        :param url: Url for request
        :param post_data: Data of POST-request if need
        :return: Text of server response
        """
        response = requests.get(url) if \
            not post_data else \
            requests.post(url, data=post_data, headers={'Content-Type': 'application/x-www-form-urlencoded'})

        if response.status_code == 403:
            raise FinderInsideProException(
                FinderInsideProException.EXCEPTION_TEXT_WRONG_KEY, FinderInsideProException.TYPE_KEY_IS_WRONG)
        elif response.status_code == 400 and response.text == FinderInsideProException.SESSION_ERROR_TEXT:
            raise FinderInsideProException(
                FinderInsideProException.SESSION_ERROR_TEXT, FinderInsideProException.TYPE_SESSION_IS_WRONG)
        elif response.status_code != 200:
            raise FinderInsideProException(
                FinderInsideProException.REQUEST_ERROR_TEXT.format(response.status_code, response.text))

        return response.text

    def get_remain_limit(self):
        """ Return passwords remain limit """
        data = self.get_xml_from_server("http://finder.insidepro.com/api/limit?apikey={0}".format(self.key))
        try:
            xml = etree.fromstring(data.encode('utf-8'))
            return int(xml.xpath('//data/hash_search/remain')[0].text)
        except (etree.XMLSyntaxError, ValueError) as ex:
            raise FinderInsideProException("XML parse error with '{0}' data and str '{1}'".format(data, str(ex)))

    def create_session(self):
        """ Create new API session """
        data = self.get_xml_from_server(
            "http://finder.insidepro.com/api/session/start?apikey={0}&type=search".format(self.key))
        try:
            xml = etree.fromstring(data.encode('utf-8'))
            self.session_id = xml.xpath('//data/session_id')[0].text
            return self.session_id
        except (etree.XMLSyntaxError, ValueError) as ex:
            raise FinderInsideProException("XML parse error with '{0}' data and str '{1}'".format(data, str(ex)))

    def parse_and_fill_hashes_from_xml(self, xml_str, hashes):
        """
        Method parse a xml-response from server with search result and return list of found hashes
        :param xml_str: String xml server response
        :param hashes: List of hashes which was sended to server. Minimum format: [{'hash': '...', 'salt': '...'}, ...]
        You can place other keys in hash-dictionary, but 'hash' and 'salt' must be there always.
        :return list: List of found hashes with hash, salt and password keys (and with other fields if they was
        in 'hashes' param). Format: [{'hash': '...', 'salt': '...', 'password': '...'}, ...]
        """
        result = []

        xml = etree.fromstring(xml_str)
        for element in xml.xpath('//d/i'):
            if element.xpath('s'):
                continue

            for _hash in hashes:
                if element.xpath('h')[0].text == _hash['hash']:
                    _hash['password'] = element.xpath('p')[0].text
                    result.append(_hash)

        return result

    def search_hashes(self, hashes):
        """
        Method send request to server for hashes search and return hashes list with found passwords (result of
        parse_and_fill_hashes_from_xml() method).
        :exception FinderInsideProException: If you give per once more hashes then limit
        :exception FinderInsideProException: If remain hashes count less minimal hashes limit per once
        :exception FinderInsideProException: If client can`t create session twice
        :param hashes: List of hashes which was sended to server. Format: [{'hash': '...', 'salt': '...'}, ...]
        :return list: List of found hashes with hash, salt and password keys (and with other fields if they was
        in 'hashes' param). Format: [{'hash': '...', 'salt': '...', 'password': '...'}, ...]
        """
        if len(hashes) > self.hashes_per_once_limit:
            raise FinderInsideProException(
                FinderInsideProException.EXCEPTION_TEXT_HASHES_COUNT_LIMIT.format(self.hashes_per_once_limit))

        if not len(self.session_id):
            self.create_session()

        if self.get_remain_limit() < self.hashes_per_once_limit:
            raise FinderInsideProException(
                FinderInsideProException.EXCEPTION_TEXT_SMALL_REMAIN, FinderInsideProException.TYPE_SMALL_REMAIN)

        hashes_list = []
        for _hash in hashes:
            hash_str = "{0}:{1}".format(_hash['hash'], _hash['salt']) if len(_hash['salt']) else _hash['hash']
            hash_str = urllib.quote_plus(hash_str)
            hashes_list.append("hash[]=" + hash_str)

        try:
            xml = self.get_xml_from_server(
                "http://finder.insidepro.com/api/hash/search?apikey={0}&session_id={1}".
                format(self.key, self.session_id),
                "&".join(hashes_list)
            )
        except FinderInsideProException as ex:
            if ex.extype == FinderInsideProException.TYPE_SESSION_IS_WRONG:
                self.create_session()

            try:
                xml = self.get_xml_from_server(
                    "http://finder.insidepro.com/api/hash/search?apikey={0}&session_id={1}".
                    format(self.key, self.session_id),
                    "&".join(hashes_list)
                )
            except FinderInsideProException as ex:
                if ex.extype == FinderInsideProException.TYPE_SESSION_IS_WRONG:
                    raise FinderInsideProException('Can`t create session, fatal error')

        return self.parse_and_fill_hashes_from_xml(xml.encode('utf-8'), hashes)
