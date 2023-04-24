"""Tests the upload_xml.py script
"""
import unittest
from unittest.mock import patch
from requests import Session
import os
import requests
import logging
logger = logging.getLogger(__name__)

class TestStringMethods(unittest.TestCase):
    @patch.object(Session, 'post')    
    def test_upload_xml(self, mock_post):

        TEST_XML_STRING = "<xml>test xml</xml>"
        write_and_upload(TEST_XML_STRING)

        self.assertIn('xml_packet', mock_post.call_args.kwargs['data'])

def write_and_upload(xml_string):
    # Upload
    session = requests.session()
    session.auth = (os.environ['UPLOAD_USER'], os.environ['UPLOAD_PASSWORD'])
    SYSTEM_ENV = os.environ.get('SYSTEM_ENV', None)
    if SYSTEM_ENV == 'PRODUCTION' or SYSTEM_ENV == 'STAGING':
        url = 'https://tracet.duckdns.org/event_create/'
    else:
        url = 'http://127.0.0.1:8000/event_create/'

    data = {
        'xml_packet': xml_string
    }
    print(url)
    return session.post(url, data=data)
