#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime as dt
import logging
import re

import requests
from bs4 import BeautifulSoup

from trojmiastopl.utils import get_content_for_url

try:
    from __builtin__ import unicode
except ImportError:
    unicode = lambda x, *args: x

log = logging.getLogger(__file__)


def get_title(offer_markup):
    """ Searches for offer title on offer page

    :param offer_markup: Class "title-wrap" from offer page markup
    :type offer_markup: str
    :return: Title of offer or None if there is no title
    :rtype: str, None

    :except: Returns None when couldn't find title of offer page.
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        return html_parser.find('h1').text.strip()
    except AttributeError:
        return


def get_img_url(offer_markup):
    """ Searches for images in offer markup

    :param offer_markup: Id "gallery" from offer page markup
    :type offer_markup: str
    :return: Images of offer in list
    :rtype: list
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    images = html_parser.find_all(class_="fancybox")
    output = []
    for img in images:
        output.append(img.attrs["href"])
    return output


def parse_region(offer_markup):
    """ Parses region information

    :param offer_markup: Class "sidebar" from offer page markup
    :type offer_markup: str
    :return: Region of offer
    :rtype: dict
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    parsed_address = html_parser.find(id="show-address").find(class_="ogl__details__desc").contents
    print(parsed_address)
    output = {"voivodeship": "Pomorskie", "city": None, "district": None}
    output["city"] = str(parsed_address[0]).replace("\xa0", "")
    # Just city
    if len(parsed_address) == 1:
        output["address"] = output["city"]
        return output
    district_parser = BeautifulSoup(str(parsed_address[1]), "html.parser")
    district = district_parser.find("a")
    # City, district, street
    if district is not None and len(parsed_address) > 2:
        output["district"] = district.text
        output["address"] = "{0}, {1}, {2}".format(
            output["city"],
            output["district"],
            str(parsed_address[3]).replace("\xa0", "")
        )
    # City, district
    elif district is not None:
        output["district"] = district.text
        output["address"] = "{0}, {1}".format(
            output["city"],
            output["district"]
        )
    # City, street
    else:
        output["address"] = "{0}, {1}".format(output["city"], str(parsed_address[2]).replace("\xa0", ""))
    return output


def get_month_num_for_string(value):
    """ Map for polish month names

    :param value: Month value
    :type value: str
    :return: Month number
    :rtype: int
    """
    value = value.lower()[:3]
    return {
        'sty': 1,
        'lut': 2,
        'mar': 3,
        'kwi': 4,
        'maj': 5,
        'cze': 6,
        'lip': 7,
        'sie': 8,
        'wrz': 9,
        'paź': 10,
        'lis': 11,
        'gru': 12,
    }.get(value)


def parse_date_to_timestamp(date):
    """ Parses string date to unix timestamp

    :param date: Date
    :type date: str
    :return: Unix timestamp
    :rtype: int
    """
    date_parts = date.split(' ')
    month = get_month_num_for_string(date_parts[1])
    year = int(date_parts[2])
    day = int(date_parts[0])
    date_added = dt.datetime(year=year, day=day, month=month)
    return int((date_added - dt.datetime(1970, 1, 1)).total_seconds())


def parse_dates_and_id(offer_markup):
    """ Searches for date of creating and date of last update of an offer. Additionally parses offer id number.

    :param offer_markup: Class "sidebar" from offer page markup
    :type offer_markup: str
    :return: Date added and date updated if found and offer id (id, added, updated)
    :rtype: dict
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    parsed_details = html_parser.find_all("li")
    output = {"updated": None}
    for detail in parsed_details:
        if "numer" in detail.text:
            output["id"] = detail.span.text
        elif "wprowadzenia" in detail.text:
            output["added"] = parse_date_to_timestamp(detail.span.text)
        elif "aktualizacja" in detail.text:
            output["updated"] = parse_date_to_timestamp(detail.span.text)
    return output


def get_surface(offer_markup):
    """ Searches for surface in offer markup

    :param offer_markup: Class "sidebar" from offer page markup
    :type offer_markup: str
    :return: Surface or None if there is no surface
    :rtype: float, None

    :except: When there is no offer surface it will return None
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        surface = html_parser.sup.parent.previous_sibling
        return float(surface.replace("m2", "").strip().replace(",", ".").replace(" ", ""))
    except AttributeError:
        return


def get_apartment_type(offer_markup):
    """ Searches for apartment type in offer markup

    :param offer_markup: Class "sidebar" from offer page markup
    :type offer_markup: str
    :return: Apartment type
    :rtype: str
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    return html_parser.find(class_="rodzaj_nieruchomosci").find(class_="dd").text.strip()


def get_available_from(offer_markup):
    """ Searches for available from in offer markup

    :param offer_markup: Class "sidebar" from offer page markup
    :type offer_markup: str
    :return: Available from or None if there is no information
    :rtype: str, None
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        return html_parser.find(class_="dostepne_od").find(class_="dd").text.strip()
    except AttributeError:
        return


def get_additional_information(offer_markup):
    """ Searches for additional info and heating type

    :param offer_markup: Class "sidebar" from offer page markup
    :type offer_markup: str
    :return: Additional info with optional heating type
    :rtype: dict
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser").find(class_="description")
    additional_info = "".join([
        part.strip()
        for i, part in enumerate(html_parser.text.split('Dodatkowe informacje'))
        if i == 1
    ])
    heating = html_parser.find('div', class_="typ_ogrzewania")
    return {
        'heating': heating.find(class_="dd").text.strip() if heating else False,
        'balcony': 'balkon' in additional_info,
        'kitchen': 'kuchnia' in additional_info,
        'terrace': 'taras' in additional_info,
        'internet': 'internet' in additional_info,
        'elevator': 'winda' in additional_info,
        'car_parking': 'parkingowe' in additional_info,
        'disabled_facilities': 'podjazd' in additional_info,
        'mezzanine': 'antresola' in additional_info,
        'basement': 'piwnica' in additional_info,
        'duplex_apartment': 'dwupoziomowe' in additional_info,
        'garden': 'ogródek' in additional_info,
        'garage': 'garaż' in additional_info,
        'cable_tv': 'kablówka' in additional_info
    }


def parse_description(description_markup):
    """ Searches for offer description

    :param description_markup: Class "ogl-description" from offer page markup
    :type description_markup: str
    :return: Offer description
    :rtype: str
    """
    html_parser = BeautifulSoup(description_markup, "html.parser").text
    # \xa0 means no-break space symbol
    return html_parser.split("$(function")[0].replace("  ", "").replace("\n", " ").replace("\r", "") \
        .replace(u'\xa0', u' ').strip()


def get_furnished(offer_markup):
    """ Searches if offer is marked as furnished or not

    :param offer_markup: Class "sidebar" from offer page markup
    :type offer_markup: str
    :return: Information is offer furnished
    :rtype: bool

    :except: If there is no information if offer is furnished it will return None
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    try:
        furniture = html_parser.find(class_="umeblowane").text
        if "tak" in furniture:
            return True
    except AttributeError:
        return None
    return False


def parse_flat_data(offer_markup):
    """ Parses flat data from sidebar

    :param offer_markup: Class "sidebar" from offer page markup
    :type offer_markup: str
    :return: Information about price, deposit, floor, number of rooms, date of built and
    total count of floors in building
    :rtype: dict
    """
    html_parser = BeautifulSoup(offer_markup, "html.parser")
    flat_data = {"pietro": None, "l_pokoi": None, "rok_budowy": None, "l_pieter": None, "cena": None, "kaucja": None}
    for element in list(flat_data.keys()):
        current = html_parser.find(class_=element)
        if current is not None:
            correct = current.text
            if "parter" in correct:
                correct = "0"
            flat_data[element] = int("".join(re.findall(r'\d+', correct)))
    return flat_data


def parse_poster_name(contact_markup):
    """ Parses poster name

    :param contact_markup: Class "contact-box" from offer page markup
    :type contact_markup: str
    :return: Poster name
    :rtype: str
    """
    html_parser = BeautifulSoup(contact_markup, "html.parser")
    poster_name = html_parser.find(class_="name")
    if poster_name is not None:
        poster_name = poster_name.text.strip()
    else:
        poster_name = None
    return poster_name


def parse_offer(url):
    """ Parses data from offer page url

    :param url: Url of current offer page
    :type url: str
    :return: Dictionary with all offer details
    :rtype: dict

    :except: If there is no offer title anymore - offer got deleted.
    """
    log.debug(url)
    response = get_content_for_url(url)
    if response is None:
        raise requests.HTTPError
    html_parser = BeautifulSoup(response.content, "html.parser")
    offer_content = str(html_parser.find(class_="form-heading__desc"))
    title = get_title(offer_content)
    if title is None:
        log.warning("Offer {0} is not available anymore.".format(url))
        return
    images = get_img_url(str(html_parser.find(id="gallery")))
    contact_content = str(html_parser.find(class_="contact-box"))
    date_details = str(html_parser.find(class_="ogl-info-wrap"))
    dates_id = parse_dates_and_id(date_details)
    description = parse_description(str(html_parser.find(class_="ogl-description")))
    offer_content = str(html_parser.find(class_="ogl__details ogl--details--left"))
    surface = get_surface(offer_content)
    flat_data = parse_flat_data(offer_content)
    address = parse_region(offer_content)
    return {
        "title": title,
        "offer_id": dates_id["id"],
        "type": get_apartment_type(offer_content),
        "address": address["address"],
        "voivodeship": address["voivodeship"],
        "city": address["city"],
        "district": address["district"],
        "price": flat_data["cena"],
        "currency": "PLN",
        "deposit": flat_data["kaucja"],
        "surface": surface,
        "price/surface": round(flat_data["cena"] / surface) if surface else None,
        "floor": flat_data["pietro"],
        "floor_count": flat_data["l_pieter"],
        "rooms": flat_data["l_pokoi"],
        "built_date": flat_data["rok_budowy"],
        "available_from": get_available_from(offer_content),
        "furniture": get_furnished(offer_content),
        "additional": get_additional_information(offer_content),
        "poster_name": parse_poster_name(contact_content),
        "date_added": dates_id["added"],
        "date_updated": dates_id["updated"],
        "date_added_readable": dt.datetime.fromtimestamp(dates_id["added"]).isoformat(),
        "date_updated_readable": dt.datetime.fromtimestamp(dates_id["updated"]).isoformat()
        if dates_id["updated"] else None,
        "url": url,
        "description": description,
        "images": images
    }
