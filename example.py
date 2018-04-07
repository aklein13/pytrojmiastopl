#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

from trojmiastopl.category import get_category
from trojmiastopl.offer import parse_offer

log = logging.getLogger(__file__)

if __name__ == '__main__':
    search_filters = {
        "offer_type": "Mieszkanie",
        "data_wprow": "3d",
        "cena[]": (2000, None)
    }
    parsed_urls = get_category("nieruchomosci-mam-do-wynajecia", "Gdańsk", **search_filters)[:3]
    for element in (parse_offer(url) for url in parsed_urls if url):
        print()
        print(element)
