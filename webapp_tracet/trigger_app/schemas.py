from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ninja import ModelSchema, Schema
from pydantic import BaseModel, Field
from trigger_app.models.event import Event, EventGroup
from trigger_app.models.observation import Observations
from trigger_app.models.proposal import ProposalDecision
from trigger_app.models.telescope import Telescope


class CommandResultSchema(Schema):
    stderr: str
    stdout: str
    command: Optional[str] = None
    retcode: int


class MWAResponseParamsSchema(Schema):
    nobs: int
    azlist: Optional[List[float]] = None
    pretty: int
    ralist: List[float]
    altlist: Optional[List[float]] = None
    calname: str
    creator: str
    declist: List[float]
    exptime: int
    freqres: float
    inttime: float
    obsname: str
    pretend: bool
    avoidsun: bool
    group_id: Optional[int] = None
    freqspecs: List[str]
    subarrays: List[str]
    calexptime: int
    project_id: str
    secure_key: str
    sourcelist: Optional[List[str]] = None
    subarraylist: List[str]


class MWAResponseSchema(Schema):
    clear: CommandResultSchema = None
    errors: Dict[str, Any] = None
    params: MWAResponseParamsSchema = None
    success: bool = None
    schedule: CommandResultSchema = None
    obsid_list: List[int] = None
    trigger_id: Union[int, str] = None


class MWAResponseSimpleSchema(Schema):
    clear: Dict[str, Any] = None
    errors: Dict[str, Any] = None
    params: Dict[str, Any] = None
    success: bool = None
    schedule: Dict[str, Any] = None
    obsid_list: List[int] = None
    trigger_id: Union[int, str] = None


class MWASubArraysSchema(Schema):
    ra: List[float] = None
    dec: List[float] = None


class EventGroupSchema(ModelSchema):
    class Meta:
        model = EventGroup
        fields = "__all__"


class ProposalDecisionSchema(ModelSchema):
    event_group_id: EventGroupSchema | None = None

    class Meta:
        model = ProposalDecision
        fields = "__all__"


class EventSchema(ModelSchema):
    event_group_id: EventGroupSchema | None = None

    class Meta:
        model = Event
        fields = "__all__"


class TelescopeSchema(ModelSchema):
    class Meta:
        model = Telescope
        fields = "__all__"


class ObservationsSchema(ModelSchema):
    telescope: TelescopeSchema
    proposal_decision_id: ProposalDecisionSchema
    event: EventSchema
    mwa_sub_arrays: Optional[MWASubArraysSchema] = None
    mwa_sky_map_pointings: Optional[str] = None
    mwa_response: Optional[MWAResponseSimpleSchema] = None

    class Meta:
        model = Observations
        fields = [
            'trigger_id',
            'website_link',
            'telescope',
            'proposal_decision_id',
            'event',
            'reason',
            'mwa_sub_arrays',
            'created_at',
            'request_sent_at',
            'mwa_sky_map_pointings',
            'mwa_response',
        ]


class ObservationCreateSchema(Schema):
    telescope_name: str
    proposal_decision_id: int
    event_id: int
    trigger_id: str
    reason: Optional[str] = None
    website_link: Optional[str] = None
    mwa_response: Optional[MWAResponseSimpleSchema] = None
    request_sent_at: Optional[datetime] = None
    mwa_sub_arrays: Optional[MWASubArraysSchema] = None
    mwa_sky_map_pointings: Optional[str] = None


class ObservationCreateResponseSchema(Schema):
    trigger_id: str
    status: str


class PydTelescope(BaseModel):
    name: str
    lon: float
    lat: float
    height: float

class PydTelescopeProjectID(BaseModel):
    id: str
    password: Optional[str] = None
    description: str
    atca_email: Optional[str] = None
    telescope: PydTelescope

class PydEventTelescope(BaseModel):
    name: str
    
class PydTelescopeSettings(BaseModel):
    telescope: PydTelescope
    maximum_observation_time_seconds: int
    event_any_duration: bool
    event_min_duration: float
    event_max_duration: float
    pending_min_duration_1: float
    pending_max_duration_1: float
    pending_min_duration_2: float
    pending_max_duration_2: float
    maximum_position_uncertainty: float
    fermi_prob: float
    swift_rate_signf: float
    antares_min_ranking: int
    repointing_limit: float
    observe_significant: bool

class PydProposalSettings(BaseModel):
    id: int
    proposal_id: str
    telescope: Optional[PydTelescope] = None
    project_id: PydTelescopeProjectID
    proposal_description: str
    priority: int = Field(default=1)
    event_telescope: Optional[PydEventTelescope] = None
    testing: Optional[str] = None
    source_type: Optional[str] = None
    telescope_settings: Optional[Dict[str, Any]] = None
    source_settings: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"