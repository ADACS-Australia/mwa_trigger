import json

import requests
from trigger_app.models.event import Event
from trigger_app.models.proposal import ProposalDecision
from trigger_app.schemas import EventSchema, ProposalDecisionSchema

# Fetch the instances from the database
prop_dec = ProposalDecision.objects.get(id=77790)
voevent_instances = Event.objects.filter(event_group_id=prop_dec.event_group_id.id)
voevent_instance = voevent_instances[0]

# Serialize the instances to JSON-compatible dictionaries
prop_dec_data_str = ProposalDecisionSchema.from_orm(prop_dec).json()
voevent_data_str = EventSchema.from_orm(voevent_instance).json()

prop_dec_data = json.loads(prop_dec_data_str)
voevent_data = json.loads(voevent_data_str)

# Prepare the payload
payload = {
    "prop_dec": prop_dec_data,
    "voevent": voevent_data,
    "observation_reason": "First observation",
}

# Define the API URL
api_url = "http://api:8000/api/worth_observing/"

# Send the POST request to the API
response = requests.post(api_url, json=payload)

# Check the response
if response.status_code == 200:
    print("Request successful:", response.json())
else:
    print("Request failed with status code:", response.status_code)
