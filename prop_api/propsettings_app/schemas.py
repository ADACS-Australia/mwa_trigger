from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ninja import ModelSchema
from propsettings_app.models import Telescope, TelescopeProjectID
from pydantic import BaseModel, Field

GRB = "GRB"
FS = "FS"
NU = "NU"
GW = "GW"
SOURCE_CHOICES = (
    (GRB, "Gamma-ray burst"),
    (FS, "Flare star"),
    (NU, "Neutrino"),
    (GW, "Gravitational wave"),
)

TRIGGER_ON = (
    ("PRETEND_REAL", "Real events only (Pretend Obs)"),
    ("BOTH", "Real events (Real Obs) and test events (Pretend Obs)"),
    ("REAL_ONLY", "Real events only (Real Obs)"),
)


# class TelescopeSchema(ModelSchema):
#     class Meta:
#         model = Telescope
#         fields = ["id", "name", "lon", "lat", "height"]


class CommandResultSchema(BaseModel):
    stderr: str
    stdout: str
    command: Optional[str] = None
    retcode: int


class MWAResponseParamsSchema(BaseModel):
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


class MWAResponseSchema(BaseModel):
    clear: CommandResultSchema
    errors: Dict[str, Any]
    params: MWAResponseParamsSchema
    success: bool
    schedule: CommandResultSchema
    obsid_list: List[int] = None
    trigger_id: Union[int, str] = None


class MWAResponseSimpleSchema(BaseModel):
    clear: Dict[str, Any] = None
    errors: Dict[str, Any] = None
    params: Dict[str, Any] = None
    success: bool = None
    schedule: Dict[str, Any] = None
    obsid_list: List[int] = None
    trigger_id: Union[int, str] = None


class MWASubArraysSchema(BaseModel):
    ra: List[float]
    dec: List[float]


class TelescopeSchema(BaseModel):
    id: int
    name: str
    lon: float
    lat: float
    height: float


class TelescopeProjectIDSchema(ModelSchema):
    telescope: TelescopeSchema | None = None

    class Meta:
        model = TelescopeProjectID
        fields = ["id", "password", "description", "atca_email", "telescope"]


class EventGroupSchema(BaseModel):
    id: int
    trig_id: str
    earliest_event_observed: Optional[datetime]
    latest_event_observed: Optional[datetime]
    ra: Optional[float]
    dec: Optional[float]
    ra_hms: Optional[str]
    dec_dms: Optional[str]
    pos_error: Optional[float]
    recieved_data: datetime
    source_type: Optional[str]
    ignored: bool
    event_observed: Optional[datetime]
    source_name: Optional[str]

    class Config:
        from_attributes = True


class ProposalDecisionSchema(BaseModel):
    id: int
    decision: str
    decision_reason: Optional[str]
    proposal: Optional[int]  # Assuming this is the ID of the related ProposalSettings
    event_group_id: EventGroupSchema  # event_group: EventGroupSchema
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


class EventSchema(BaseModel):
    id: int
    event_group_id: EventGroupSchema
    trig_id: Optional[str]
    self_generated_trig_id: bool
    telescope: Optional[str]
    sequence_num: Optional[int]
    event_type: Optional[str]
    role: Optional[str]
    duration: Optional[float]
    ra: Optional[float]
    dec: Optional[float]
    ra_hms: Optional[str]
    dec_dms: Optional[str]
    pos_error: Optional[float]
    recieved_data: datetime
    event_observed: Optional[datetime]
    xml_packet: str
    ignored: bool
    source_name: Optional[str]
    source_type: Optional[str]

    fermi_most_likely_index: Optional[float]
    fermi_detection_prob: Optional[float]
    swift_rate_signif: Optional[float]
    antares_ranking: Optional[int]
    hess_significance: Optional[float]

    lvc_false_alarm_rate: Optional[str]
    lvc_significant: Optional[bool]
    lvc_event_url: Optional[str]
    lvc_binary_neutron_star_probability: Optional[float]
    lvc_neutron_star_black_hole_probability: Optional[float]
    lvc_binary_black_hole_probability: Optional[float]
    lvc_terrestial_probability: Optional[float]
    lvc_includes_neutron_star_probability: Optional[float]
    lvc_retraction_message: Optional[str]
    lvc_skymap_fits: Optional[str]
    lvc_prob_density_tile: Optional[float]
    lvc_skymap_file: Optional[str]
    lvc_instruments: Optional[str]
    lvc_false_alarm_rate: Optional[str]

    class Config:
        from_attributes = True


class LatestObservationSchema(BaseModel):

    telescope: TelescopeSchema
    proposal_decision_id: ProposalDecisionSchema
    event: EventSchema
    trigger_id: str
    website_link: Optional[str] = None
    reason: Optional[str] = None
    mwa_sub_arrays: Optional[MWASubArraysSchema] = None
    created_at: datetime
    request_sent_at: Optional[datetime] = None
    mwa_sky_map_pointings: Optional[str] = None
    mwa_response: Optional[MWAResponseSimpleSchema] = None

    class Config:
        from_attributes = True


class ObservationSchema(BaseModel):

    telescope: TelescopeSchema
    proposal_decision_id: ProposalDecisionSchema
    event: EventSchema
    trigger_id: str
    website_link: Optional[str] = None
    reason: Optional[str] = None
    mwa_sub_arrays: Optional[MWASubArraysSchema] = None
    created_at: datetime
    request_sent_at: Optional[datetime] = None
    mwa_sky_map_pointings: Optional[str] = None
    mwa_response: Optional[MWAResponseSchema] = None

    class Config:
        from_attributes = True
