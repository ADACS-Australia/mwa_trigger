import logging

from django.shortcuts import get_object_or_404
from ninja import NinjaAPI, Path, Router
from ninja_jwt.authentication import JWTAuth
from trigger_app.models.event import Event, EventGroup
from trigger_app.models.observation import Observations
from trigger_app.models.proposal import ProposalDecision
from trigger_app.models.telescope import Telescope
from trigger_app.schemas import (EventGroupSchema, EventSchema,
                                 ObservationCreateResponseSchema,
                                 ObservationCreateSchema, ObservationsSchema,
                                 ProposalDecisionSchema, TelescopeSchema)

json_logger = logging.getLogger('django_json')
# Initialize the Ninja API
# app = NinjaAPI()
app = Router(auth=JWTAuth())

@app.get("telescope/{id}/", response=TelescopeSchema)
def get_telescope_by_id(request, id: int):
    return get_object_or_404(Telescope, pk=id)


@app.get("eventgroup/{id}/", response=EventGroupSchema)
def get_event_group_by_id(request, id: int):
    return EventGroup.objects.get(pk=id)


@app.get("proposaldecision/{id}/", response=ProposalDecisionSchema)
def get_proposal_decision_by_id(request, id: int):
    return ProposalDecision.objects.get(id=id)


@app.get("event/{id}/", response=EventSchema)
def get_event_by_id(request, id: int):
    return Event.objects.get(pk=id)


@app.get("observation/{id}/", response=ObservationsSchema)
def get_observation_by_id(request, id: str):
    observation = get_object_or_404(Observations, trigger_id=id)
    return ObservationsSchema.from_orm(observation)


# @app.get("observations/", response=list[ObservationsSchema])
# def list_observations(request):
#     return Observations.objects.order_by('-trigger_id')[
#         :100
#     ]  # Get latest 100 observations


@app.post("/create-observation/", response=ObservationCreateResponseSchema)
def create_observation(request, payload: ObservationCreateSchema):
    # Get related objects
    print("DEBUG - payload starts: \n")
    print(payload)
    print("DEBUG - payload ends \n")
    telescope = get_object_or_404(Telescope, name=payload.telescope_name)
    proposal_decision = get_object_or_404(
        ProposalDecision, id=payload.proposal_decision_id
    )
    event = get_object_or_404(Event, id=payload.event_id)
    # Convert nested schemas to dictionaries
    reason = payload.reason if payload.reason else None
    website_link = payload.website_link if payload.website_link else ""
    request_sent_at = payload.request_sent_at if payload.request_sent_at else None
    mwa_response = payload.mwa_response.dict() if payload.mwa_response else None
    mwa_sub_arrays = payload.mwa_sub_arrays.dict() if payload.mwa_sub_arrays else None
    mwa_sky_map_pointings = (
        payload.mwa_sky_map_pointings if payload.mwa_sky_map_pointings else None
    )
    print("DEBUG - telescope:", telescope)
    print("DEBUG - mwa_sub_arrays starts:", mwa_sub_arrays)
    
    json_logger.info(
        "Created observation",
        extra={
            "function": "create_observation",
            "event_id": event.id,
            "trig_id": proposal_decision.trig_id,
        },
    )

    # Create the Observation
    # observation = Observations.objects.create(
    #     trigger_id=payload.trigger_id,
    #     telescope=telescope,
    #     proposal_decision_id=proposal_decision,
    #     event=event,
    #     reason=reason,
    #     website_link=website_link,
    #     mwa_response=mwa_response,
    #     request_sent_at=request_sent_at,
    #     mwa_sub_arrays=mwa_sub_arrays,
    #     mwa_sky_map_pointings=mwa_sky_map_pointings,
    # )

    print("observation created")
    # observation.trigger_id
    # observation.trigger_id
    return ObservationCreateResponseSchema(trigger_id="1111111", status="created")


@app.get("/latest-observation/{telescope_name}/", response=ObservationsSchema, auth=None)
def get_latest_observation(request, telescope_name: str):
    telescope = get_object_or_404(Telescope, name=telescope_name)
    print("telescope found:", telescope)
    latest_observation = (
        Observations.objects.filter(telescope=telescope).order_by("-created_at").first()
    )
    print("latest_observation", latest_observation.mwa_response)
    if latest_observation:
        return ObservationsSchema.from_orm(latest_observation)
    return {"error": "No observations found for this telescope"}
