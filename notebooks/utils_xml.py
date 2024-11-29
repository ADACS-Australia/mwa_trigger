import os
import xml.etree.ElementTree as ET

import requests
import voeventparse
import xmltodict
from lxml import etree


def voevent_to_dict(xml_content):
    """
    Converts a VOEvent XML string to a Python dictionary.

    Parameters:
        xml_content (str): The VOEvent XML data as a string.

    Returns:
        dict: A Python dictionary representation of the VOEvent.
    """
    try:
        # Parse the XML content using xmltodict
        voevent_dict = xmltodict.parse(xml_content)
        return voevent_dict
    except Exception as e:
        print(f"Error parsing VOEvent: {e}")
        return None


def modify_xml_content(xml_content, updates):
    """
    Modify XML content using ElementTree.

    Parameters:
        xml_content (str): Original XML string
        updates (dict): Dictionary of xpath-like strings and new values

    Returns:
        str: Modified XML string
    """
    # Parse the XML string
    root = ET.fromstring(xml_content)

    # Example modifications
    for xpath, new_value in updates.items():
        element = root.find(xpath)
        if element is not None:
            element.text = str(new_value)

    # Convert back to string
    return ET.tostring(root, encoding='unicode')


def modify_swift_trigid(xml_content, new_trigid):
    """
    Modify TrigID in the XML content using lxml.

    Parameters:
        xml_content (str): Original XML string
        new_trigid (str): New TrigID value

    Returns:
        str: Modified XML string
    """
    root = etree.fromstring(xml_content.encode())

    # Find the TrigID parameter
    trigid_param = root.xpath("//Param[@name='TrigID']")[0]
    trigid_param.set('value', str(new_trigid))

    return etree.tostring(root, pretty_print=True, encoding='unicode')


def modify_swift_dates(xml_content, new_date, new_isotime):
    """
    Modify both date fields in the XML content.

    Parameters:
        xml_content (str): Original XML string
        new_date (str): New date for the Who/Date field
        new_isotime (str): New date for the ISOTime field

    Returns:
        str: Modified XML string
    """
    root = etree.fromstring(xml_content.encode())

    # Modify the Date in Who section
    date_element = root.xpath("//Who/Date")[0]
    date_element.text = new_date

    # Modify the ISOTime
    isotime_element = root.xpath("//ISOTime")[0]
    isotime_element.text = new_isotime

    return etree.tostring(root, pretty_print=True, encoding='unicode')


def write_and_upload(xml_string):

    # Upload
    session = requests.session()
    session.auth = (os.environ["UPLOAD_USER"], os.environ["UPLOAD_PASSWORD"])
    SYSTEM_ENV = os.environ.get("SYSTEM_ENV", None)
    if SYSTEM_ENV == "PRODUCTION" or SYSTEM_ENV == "STAGING":
        url = "https://tracet.duckdns.org/event_create/"
    else:
        url = "http://127.0.0.1:8000/event_create/"

    data = {"xml_packet": xml_string}
    response = session.post(url, data=data)
    return response


def modify_lvc_dates(xml_content, new_date):
    """
    Modify GraceID and update dates in LVC XML content.

    Parameters:
        xml_content (str): Original XML string
        new_graceid (str): New GraceID value
        new_date (str): New date in ISO format (e.g., '2024-11-27T20:24:27Z')

    Returns:
        str: Modified XML content
    """
    root = etree.fromstring(xml_content.encode())

    # Update dates
    # 1. Update Who/Date
    date_element = root.xpath("//Who/Date")[0]
    date_element.text = new_date

    # 2. Update ISOTime
    isotime_element = root.xpath("//WhereWhen//ISOTime")[0]
    isotime_element.text = new_date

    return etree.tostring(root, pretty_print=True, encoding='unicode')
