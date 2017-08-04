#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

import requests
from bs4 import BeautifulSoup
from scrapper_helpers.utils import caching

from trojmiastopl import BASE_URL

log = logging.getLogger(__file__)

SEARCH_URL = "https://ogloszenia.trojmiasto.pl/szukaj/"
OBFUSCATOR_URL = "http://ogloszenia.trojmiasto.pl/_ajax/obfuscator/?decode"


def flatten(container):
    """ Flattens a list

    :param container: list with nested lists
    :type container: list
    :return: list with elements that were nested in container
    :rtype: list
    """
    for i in container:
        if isinstance(i, (list, tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i


def decode_type(filter_value):
    """ Decodes offer type name to it's value

    List of available options and it's translation can be found bellow.

    :param filter_value: One of available type names
    :type filter_value: str
    :return: Int value for POST variable
    :rtype: int
    """
    available = {
        "Mieszkanie": 100,  # flat
        "Pokoj": 395,  # room
        "Biuro": 400,  # office
        "Dom": 200,  # house
        "Blizniak": 230,  # semi-detached house
        "Kamienica": 250,  # tenement house
        "Pietrowy": 260,  # storey house
        "Rekreacyjny": 220,  # leisure house
        "Szeregowy": 240,  # terraced house
        "Wolnostojacy": 210,  # detached house
        "Lokal usługowy": 450  # service area
    }
    return available.get(filter_value, 0)


def get_url_for_filters(payload):
    """ Parses url from trojmiasto.pl search engine using POST method for given payload of data

    :param payload: Tuple of tuples containing POST key and argument
    :type payload: tuple
    :return: Url generated by trojmiasto.pl search engine
    :rtype: str
    """
    response = requests.post(SEARCH_URL, payload)
    html_parser = BeautifulSoup(response.content, "html.parser")
    url = html_parser.find(rel="alternate").attrs['href'].replace("/m.", "/")
    return url


def get_url(category, region=None, **filters):
    """ Creates url for given parameters

    :param category: Search category
    :param region: Search region
    :param filters: Dictionary with additional filters. See :meth:'trojmiastopl.get_category' for reference
    :type category: str
    :type region: str
    :type filters: dict
    :return: Url for given parameters
    :rtype: str
    """
    url = "/".join([BASE_URL, category]) + "/"
    if filters:
        if region is not None:
            payload = (("id_kat", 104), ("s", region))
        else:
            payload = (("id_kat", 104),)
        for k, v in filters.items():
            if isinstance(v, tuple):
                if v[0] is None:
                    v[0] = 0
                if v[1] is None:
                    payload += (k, v[0]),
                    continue
                payload += (k, v[0]), (k, v[1])
                continue
            elif "offer_type" == k:
                v = decode_type(v)
                k = "wi"
            elif "data_wprow" == k:
                available = ["1d", "3d", "1w", "3w"]
                if v not in available:
                    continue
            payload += (k, v),
        url = get_url_for_filters(payload)
    elif region is not None:
        url += "s,{0}.html".format(region)
    return url


def obfuscator_request(contact_hash, cookie):
    """ Sends request to http://ogloszenia.trojmiasto.pl/_ajax/obfuscator/?decode

    :param contact_hash: Data hash needed to decode information
    :type contact_hash: str
    :return: Response returned by request
    """
    response = requests.post(OBFUSCATOR_URL, data={"hash": contact_hash, "type": "ogloszenia"}, headers={"cookie": "{0}".format(cookie)})
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.warning('Request for {0} failed. Error: {1}'.format(OBFUSCATOR_URL, e))
        return None
    return response


def get_cookie_from(response):
    """
    :param response: a requests.response object
    :rtype: string
    :return: cookie information as string
    """
    cookie = response.headers['Set-Cookie'].split(';')[0]
    return cookie

@caching
def get_content_for_url(url):
    """ Connects with given url

    If environmental variable DEBUG is True it will cache response for url in /var/temp directory

    :param url: Website url
    :type url: str
    :return: Response for requested url
    """
    response = requests.get(url)
    try:
        response.raise_for_status()
    except requests.HTTPError as e:
        log.warning('Request for {0} failed. Error: {1}'.format(url, e))
        return None
    return response
