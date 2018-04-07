#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from re import findall

import requests
from bs4 import BeautifulSoup
from scrapper_helpers.utils import flatten

from trojmiastopl.utils import get_content_for_url, get_url

log = logging.getLogger(__file__)
logging.basicConfig(level=logging.DEBUG)


def get_page_count(markup):
    """ Reads total page number from trojmiasto.pl search page

    :param markup: trojmiasto.pl search page markup
    :type markup: str
    :return: Total page number
    :rtype: int

    :except: If no page number was found - there is just one page.
    """

    html_parser = BeautifulSoup(markup, "html.parser")
    page_numbers = html_parser.find(class_='pagination__page').findAll('li')
    pages = []
    for page_number in page_numbers:
        page_link = page_number.find('a')
        if page_link and 'następna' not in page_link:
            pages.append(int(page_link.text))
    return max(pages) if len(pages) > 0 else 1


def get_page_count_for_filters(category, region=None, **filters):
    """ Reads total page number for given search filters

    :param category: Search category
    :param region: Search region
    :param filters: See :meth category.get_category for reference
    :type category: str
    :type region: str
    :type filters: dict
    :return: Total page number
    :rtype: int

    :except: If no page number was found - there is just one page.
    """
    url = get_url(category, region, **filters)
    response = get_content_for_url(url)
    html_parser = BeautifulSoup(response.content, "html.parser")
    page_numbers = html_parser.find(class_='pagination__page').findAll('li')
    pages = []
    for page_number in page_numbers:
        page_link = page_number.find('a')
        if page_link and 'następna' not in page_link:
            pages.append(int(page_link.text))
    return max(pages) if len(pages) > 0 else 1


def parse_offer_url(markup):
    """ Searches for offer links in markup

    :param markup: Search page markup
    :type markup: str
    :return: Url with offer
    :rtype: str
    """
    html_parser = BeautifulSoup(markup, "html.parser")
    url = html_parser.find('a').attrs['href']
    return url


def parse_available_offers(markup):
    """ Collects all offer links on search page markup

    :param markup: Search page markup
    :type markup: str
    :return: Links to offer on given search page
    :rtype: list
    """
    html_parser = BeautifulSoup(markup, "html.parser")
    offers = html_parser.find_all(class_='list__item__content__title')
    parsed_offers = [parse_offer_url(str(offer)) for offer in offers if offer]
    return parsed_offers


def get_category(category, region=None, **filters):
    """ Parses available offer urls from given category from every page

    :param category: Search category
    :param region: Search region
    :param filters: Dictionary with additional filters. Following example dictionary contains every possible filter
    with examples of it's values.

    :Example:

    input_dict = {
        "offer_type": "Mieszkanie", # offer type. See :meth:`utils.decode_type' for reference
        "cena[]": (300, None), # price (from, to). None if you don't want to pass one of arguments
        "kaucja[]: (100,1000), # deposit
        "cena_za_m2[]": (5, 100), # price/surface
        "powierzchnia[]": (23, 300), # surface
        "l_pokoi[]": (2, 5), # desired number of rooms
        "pietro[]": (-1, 6), # desired floor, enum: from 1 to 49 and -1 (ground floor)
        "l_pieter[]": (1, 10), # desired total number of floors in building
        "rok_budowy[]": (2003, 2017), # date of built
        "data_wprow": "1d" # date of adding offer. Available: 1d - today, 3d - 3 days ago, 1w - one week ago,
         #                   3w - 3 weeks ago
    }

    :type category: str
    :type region: str
    :type filters: dict
    :return: List of all offers for given parameters
    :rtype: list
    """
    current_url = get_url(category, region, **filters)
    url = current_url
    parsed_urls, page = [], 0
    response = get_content_for_url(url)
    page_max = get_page_count(response.content)
    while page < page_max:
        if page != 0:
            url = current_url + "?strona={0}".format(page)
        log.debug(url)
        response = get_content_for_url(url)
        log.info("Loaded page {0} of offers".format(page + 1))
        offers = parse_available_offers(response.content)
        if offers is None:
            break
        parsed_urls.append(offers)
        if page is None:
            page = 1
        page += 1
    parsed_urls = list(flatten(parsed_urls))
    log.info("Loaded {0} offers".format(str(len(parsed_urls))))
    return parsed_urls


def get_offers_for_page(category, region, page, **filters):
    """ Parses offers for one specific page of given category with filters.

    :param category: Search category
    :param region: Search region
    :param page: Page number
    :param filters: See :meth category.get_category for reference
    :type category: str
    :type region: str
    :type page: int
    :type filters: dict
    :return: List of all offers for given page and parameters
    :rtype: list
    """
    try:
        url = get_url(category, region, **filters) + "?strona={0}".format(page)
        response = get_content_for_url(url)
    except requests.HTTPError as e:
        log.warning('Request failed. Error: {0}'.format(e))
        raise requests.HTTPError
    log.info("Loaded page {0} of offers".format(page))
    offers = parse_available_offers(response.content)
    log.info("Loaded {0} offers".format(str(len(offers))))
    return offers
