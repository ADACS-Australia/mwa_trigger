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
                                 ProposalDecisionSchema, TelescopeSchema,
                                 TriggerAlertsSchema, UpdateEventGroupSchema,
                                 UpdateProposalDecisionSchema)

from .utils.utils_alerts import send_all_alerts

# Initialize the Ninja API
# app = NinjaAPI()
app = Router(auth=JWTAuth())

@app.get("telescope/{id}/", response=TelescopeSchema)
def get_telescope_by_id(request, id: int):
    return get_object_or_404(Telescope, pk=id)


@app.get("eventgroup/{id}/", response=EventGroupSchema, auth=None)
def get_event_group_by_id(request, id: int):
    return EventGroup.objects.get(pk=id)

@app.put("/event-group/{event_group_id}/")
def update_event_group(request, event_group_id: int, data: UpdateEventGroupSchema):
    event_group = get_object_or_404(EventGroup, id=event_group_id)
    print("DEBUG - event_group:", event_group)
    
    for field, value in data.dict(exclude_unset=True).items():
        setattr(event_group, field, value)
    
    event_group.save()
    print("DEBUG - event_group updated:", event_group)
    return {"status": "success", "message": "EventGroup updated successfully"}

@app.get("proposaldecision/{id}/", response=ProposalDecisionSchema)
def get_proposal_decision_by_id(request, id: int):
    return ProposalDecision.objects.get(id=id)


@app.put("/proposal-decision/{proposal_decision_id}/")
def update_proposal_decision(request, proposal_decision_id: int, data: UpdateProposalDecisionSchema):
    proposal_decision = get_object_or_404(ProposalDecision, id=proposal_decision_id)
    
    proposal_decision.decision = data.decision
    proposal_decision.decision_reason = data.decision_reason
    proposal_decision.save()
    
    print("DEBUG - proposal_decision updated:", proposal_decision)

    return {"status": "success", "message": "ProposalDecision updated successfully"}


@app.get("event/{id}/", response=EventSchema)
def get_event_by_id(request, id: int):
    return Event.objects.get(pk=id)


@app.get("observation/{id}/", response=ObservationsSchema)
def get_observation_by_id(request, id: str):
    observation = get_object_or_404(Observations, trigger_id=id)
    return ObservationsSchema.from_orm(observation)


@app.post("/create-observation/") 
def create_observation(request, payload: ObservationCreateSchema):
    # Get related objects

    telescope = get_object_or_404(Telescope, name=payload.telescope_name)
    prop_dec = get_object_or_404(
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

    # Create the Observation
    observation = Observations.objects.create(
        trigger_id=payload.trigger_id,
        telescope=telescope,
        proposal_decision_id=prop_dec,
        event=event,
        reason=reason,
        website_link=website_link,
        mwa_response=mwa_response,
        request_sent_at=request_sent_at,
        mwa_sub_arrays=mwa_sub_arrays,
        mwa_sky_map_pointings=mwa_sky_map_pointings,
    )
    
    print("DEBUG - observation created:",observation.trigger_id)

    return {"message": "Observation created successfully", "trigger_id": observation.trigger_id}


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

@app.post("/trigger-alerts/")
def trigger_alerts(request, payload: TriggerAlertsSchema):
    try:
        prop_dec = get_object_or_404(ProposalDecision, id=payload.prop_dec_id)
        
        # Call send_all_alerts with the received parameters
        send_all_alerts(trigger_bool=payload.trigger_bool, debug_bool=payload.debug_bool, pending_bool=payload.pending_bool, prop_dec=prop_dec)
        # send_all_alerts(trigger_bool, debug_bool, pending_bool, prop_dec)
        print("DEBUG - successfully triggered alerts:", prop_dec.id)

        return {"message": f"Alerts triggered successfully for prop_dec.id: {prop_dec.id}"}
    except Exception as e:
        return {"error": str(e)}
