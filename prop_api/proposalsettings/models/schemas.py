
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from .event import Event, EventGroup


class ProposalDecision(BaseModel):
    id: int
    decision: str
    decision_reason: Optional[str]
    proposal: Optional[int]  # Assuming this is the ID of the related ProposalSettings
    event_group_id: EventGroup  # event_group: EventGroupSchema
    trig_id: Optional[str]
    duration: Optional[float]
    ra: Optional[float]
    dec: Optional[float]
    alt: Optional[float]
    az: Optional[float]
    ra_hms: Optional[str]
    dec_dms: Optional[str]
    pos_error: Optional[float]
    recieved_data: datetime

    class Config:
        from_attributes = True


class MWAResponseSimple(BaseModel):
    clear: Dict[str, Any] = None
    errors: Dict[str, Any] = None
    params: Dict[str, Any] = None
    success: bool = None
    schedule: Dict[str, Any] = None
    obsid_list: List[int] = None
    trigger_id: Union[int, str] = None


class MWASubArrays(BaseModel):
    ra: List[float]
    dec: List[float]


class TelescopeSchema(BaseModel):
    id: int
    name: str
    lon: float
    lat: float
    height: float


class Observations(BaseModel):

    telescope: TelescopeSchema
    proposal_decision_id: ProposalDecision
    event: Event
    trigger_id: str
    website_link: Optional[str] = None
    reason: Optional[str] = None
    mwa_sub_arrays: Optional[MWASubArrays] = None
    created_at: datetime
    request_sent_at: Optional[datetime] = None
    mwa_sky_map_pointings: Optional[str] = None
    mwa_response: Optional[MWAResponseSimple] = None

    class Config:
        from_attributes = True

