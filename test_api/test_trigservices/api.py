import json
import logging
from datetime import datetime
from random import randint
from typing import Any, Dict, List, Optional, Union
from urllib.parse import parse_qs

from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Path, Query, Schema
from pydantic import BaseModel

from .consts import DEFAULT_ATCA_RESPONSE, DEFAULT_MWA_RESPONSE

logger = logging.getLogger(__name__)

# Initialize the Ninja API
app = NinjaAPI()


class SimpleRequest(Schema):
    authToken: str
    email: str


class FrequencyBandSchema(Schema):
    use: bool
    exposureLength: str
    freq1: Optional[int]
    freq2: Optional[int]


class RequestSchema(Schema):
    source: str
    rightAscension: str
    declination: str
    project: str
    maxExposureLength: str
    minExposureLength: str
    scanType: str
    mm3: FrequencyBandSchema
    mm7: FrequencyBandSchema
    mm15: FrequencyBandSchema
    cm4: FrequencyBandSchema
    cm16: FrequencyBandSchema


class ATCAProposalRequestSchema(Schema):
    authToken: str
    email: str
    request: str


class ATCASimpleResponse(Schema):
    id: str
    text: str
    status: str
    authenticationToken: Optional[Dict[str, bool]] = None

    class Config:
        extra = "allow"  # This allows additional fields to be included without raising an error


class MWAProposalBufferRequestSchema(Schema):
    secure_key: str
    pretend: bool
    start_time: int
    obstime: int


class MWASimpleResponse(Schema):
    id: str
    text: str
    status: str


# Define the schemas for the response
class BandDetailsSchema(Schema):
    use: bool
    exposureLength: str
    freq1: int
    freq2: int


class MWAScheduleSchema(Schema):
    received: bool
    valid: bool
    targetName: str
    stderr: str
    stdout: str


class MWAResponseStrictSchema(Schema):
    id: str
    text: str
    success: bool
    obsid_list: List[int]
    trigger_id: Union[int, str] = None
    schedule: MWAScheduleSchema


class FlexibleSchema(BaseModel):
    class Config:
        extra = "allow"

    def __init__(self, **data):
        super().__init__(**data)
        for key, value in data.items():
            if isinstance(value, dict):
                setattr(self, key, FlexibleSchema(**value))
            elif isinstance(value, list):
                setattr(
                    self,
                    key,
                    [
                        FlexibleSchema(**item) if isinstance(item, dict) else item
                        for item in value
                    ],
                )


class ATCAResponse(FlexibleSchema):
    pass


class MWAResponseSchema(FlexibleSchema):
    pass


# If you want to maintain some structure and type hints, you can define a base schema:
class MWABaseSchema(Schema):
    clear: Dict[str, Any]
    errors: Dict[str, Any]
    params: Dict[str, Any]
    success: bool
    schedule: Dict[str, Any]
    obsid_list: List[Any]
    trigger_id: Union[int, str] = None

    class Config:
        extra = "allow"


JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]


def parse_json(data: JSONValue) -> Union[FlexibleSchema, JSONValue]:
    if isinstance(data, dict):
        return FlexibleSchema(**data)
    elif isinstance(data, list):
        return [parse_json(item) for item in data]
    else:
        return data


@app.post("/atca_proposal_request/", response={200: ATCAResponse})
def atca_proposal_request(request):
    """
    # Deserialize the nested objects
    """
    body_data = request.body.decode()
    parsed_data = parse_qs(body_data)

    print("data:", parsed_data)
    print("PROCESSING ATCA data")
    
    # Extract the main parameters
    auth_token = parsed_data.get('authToken', [None])[0]
    email = parsed_data.get('email', [None])[0]
    test = parsed_data.get('test', [None])[0] == 'True'
    no_time_limit = parsed_data.get('noTimeLimit', [None])[0] == 'True'
    no_score_limit = parsed_data.get('noScoreLimit', [None])[0] == 'True'
    
    request_json = json.loads(parsed_data.get('request', ['{}'])[0])
    
    print("Processed data:")
    print(f"Auth Token: {auth_token}")
    print(f"Email: {email}")
    print(f"Test: {test}")
    print(f"No Time Limit: {no_time_limit}")
    print(f"No Score Limit: {no_score_limit}")
    print("Request JSON:")
    print(json.dumps(request_json, indent=2))
    
    response_data = DEFAULT_ATCA_RESPONSE
    response_data["id"] = str(randint(100000, 999999))

    return response_data


@app.post("/mwa_proposal_request/triggerbuffer", response={200: MWAResponseSchema})
def mwa_proposal_request(request, project_id: str = Query(...)):
    """
    Handle the MWA proposal request, including query parameters and POST data
    """
    print("API received request for project_id:", project_id)

    # Parse the form data manually from request.body
    body_data = request.body.decode()  # Decode the byte string
    parsed_data = parse_qs(body_data)  # Parse the URL-encoded data
    print("Parsed data:", parsed_data)

    # Extract the POST parameters from the parsed data
    secure_key = parsed_data.get('secure_key', [None])[0]
    pretend = parsed_data.get('pretend', [None])[0]
    start_time = parsed_data.get('start_time', [None])[0]
    obstime = parsed_data.get('obstime', [None])[0]

    print(
        f"Data received: secure_key={secure_key}, pretend={pretend}, start_time={start_time}, obstime={obstime}"
    )

    response_data = DEFAULT_MWA_RESPONSE
    response_data["trigger_id"] = "TEST" + str(randint(100000, 10000000))

    return response_data


@app.post("/mwa_proposal_request/triggervcs", response={200: MWAResponseSchema})
def mwa_proposal_request(
    request, project_id: str = Query(...), obsname: str = Query(...)
):
    """
    Handle the MWA proposal request, including query parameters and POST data
    """
    print("API received request for project_id:", project_id)

    # Parse the form data manually from request.body
    body_data = request.body.decode()  # Decode the byte string
    parsed_data = parse_qs(body_data)  # Parse the URL-encoded data
    print("Parsed data:", parsed_data)

    # Output the parsed data
    for key, value in parsed_data.items():
        print(f"{key}: {value[0]}")

    response_data = DEFAULT_MWA_RESPONSE
    response_data["trigger_id"] = "TEST" + str(randint(100000, 10000000))

    return response_data
