import json
import os


def load_json_config(env_var_name):
    try:
        return json.loads(os.environ.get(env_var_name, '{}'))
    except json.JSONDecodeError:
        print(f"Error decoding JSON from {env_var_name}")
        return {}


PROJECT_PASSWORDS = load_json_config('PROJECT_PASSWORDS')
ATCA_AUTH = load_json_config('ATCA_AUTH')

ATCA_BASEURL = os.getenv(
    "ATCA_BASEURL", 'http://test-api:8000/api/atca_proposal_request/'
)
ATCA_PROTOCOL = ATCA_BASEURL.split("//")[0] + "//"
ATCA_SERVER_NAME = ATCA_BASEURL.split("//")[1].split("/")[0]
ATCA_API_ENDPOINT = ATCA_BASEURL[len(ATCA_PROTOCOL) + len(ATCA_SERVER_NAME) :]
