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