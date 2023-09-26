# generated by datamodel-codegen:
#   filename:  root.schema.json

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BasinTime(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    time: datetime
    precipitation: float
    infiltration: float
    urban_runoff: float
    node_id: int
    potential_evaporation: float
    drainage: float


class DiscreteControlLogic(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    truth_state: str
    node_id: int
    control_state: str


class Edge(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    edge_type: str
    fid: int
    to_node_id: int
    from_node_id: int


class FlowBoundaryTime(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    time: datetime
    flow_rate: float
    node_id: int


class UserStatic(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    priority: int
    active: Optional[bool] = None
    demand: float
    return_factor: float
    min_level: float
    node_id: int


class PumpStatic(BaseModel):
    max_flow_rate: Optional[float] = None
    remarks: str = Field("", description="a hack for pandera")
    active: Optional[bool] = None
    flow_rate: float
    node_id: int
    control_state: Optional[str] = None
    min_flow_rate: Optional[float] = None


class LevelBoundaryStatic(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    active: Optional[bool] = None
    node_id: int
    level: float


class UserTime(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    priority: int
    time: datetime
    demand: float
    return_factor: float
    min_level: float
    node_id: int


class DiscreteControlCondition(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    greater_than: float
    listen_feature_id: int
    node_id: int
    variable: str
    look_ahead: Optional[float] = None


class LinearResistanceStatic(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    active: Optional[bool] = None
    node_id: int
    resistance: float
    control_state: Optional[str] = None


class FractionalFlowStatic(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    node_id: int
    fraction: float
    control_state: Optional[str] = None


class PidControlStatic(BaseModel):
    integral: float
    remarks: str = Field("", description="a hack for pandera")
    listen_node_id: int
    active: Optional[bool] = None
    proportional: float
    node_id: int
    target: float
    derivative: float
    control_state: Optional[str] = None


class PidControlTime(BaseModel):
    integral: float
    remarks: str = Field("", description="a hack for pandera")
    listen_node_id: int
    time: datetime
    proportional: float
    node_id: int
    target: float
    derivative: float
    control_state: Optional[str] = None


class ManningResistanceStatic(BaseModel):
    length: float
    manning_n: float
    remarks: str = Field("", description="a hack for pandera")
    active: Optional[bool] = None
    profile_width: float
    node_id: int
    profile_slope: float
    control_state: Optional[str] = None


class FlowBoundaryStatic(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    active: Optional[bool] = None
    flow_rate: float
    node_id: int


class OutletStatic(BaseModel):
    max_flow_rate: Optional[float] = None
    remarks: str = Field("", description="a hack for pandera")
    active: Optional[bool] = None
    min_crest_level: Optional[float] = None
    flow_rate: float
    node_id: int
    control_state: Optional[str] = None
    min_flow_rate: Optional[float] = None


class Node(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    fid: int
    type: str


class TabulatedRatingCurveTime(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    time: datetime
    node_id: int
    discharge: float
    level: float


class TabulatedRatingCurveStatic(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    active: Optional[bool] = None
    node_id: int
    discharge: float
    level: float
    control_state: Optional[str] = None


class LevelBoundaryTime(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    time: datetime
    node_id: int
    level: float


class BasinState(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    node_id: int
    level: float


class BasinProfile(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    area: float
    node_id: int
    level: float


class TerminalStatic(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    node_id: int


class BasinStatic(BaseModel):
    remarks: str = Field("", description="a hack for pandera")
    precipitation: float
    infiltration: float
    urban_runoff: float
    node_id: int
    potential_evaporation: float
    drainage: float


class Root(BaseModel):
    BasinTime: Optional[BasinTime] = None
    DiscreteControlLogic: Optional[DiscreteControlLogic] = None
    Edge: Optional[Edge] = None
    FlowBoundaryTime: Optional[FlowBoundaryTime] = None
    UserStatic: Optional[UserStatic] = None
    PumpStatic: Optional[PumpStatic] = None
    LevelBoundaryStatic: Optional[LevelBoundaryStatic] = None
    UserTime: Optional[UserTime] = None
    DiscreteControlCondition: Optional[DiscreteControlCondition] = None
    LinearResistanceStatic: Optional[LinearResistanceStatic] = None
    FractionalFlowStatic: Optional[FractionalFlowStatic] = None
    PidControlStatic: Optional[PidControlStatic] = None
    PidControlTime: Optional[PidControlTime] = None
    ManningResistanceStatic: Optional[ManningResistanceStatic] = None
    FlowBoundaryStatic: Optional[FlowBoundaryStatic] = None
    OutletStatic: Optional[OutletStatic] = None
    Node: Optional[Node] = None
    TabulatedRatingCurveTime: Optional[TabulatedRatingCurveTime] = None
    TabulatedRatingCurveStatic: Optional[TabulatedRatingCurveStatic] = None
    LevelBoundaryTime: Optional[LevelBoundaryTime] = None
    BasinState: Optional[BasinState] = None
    BasinProfile: Optional[BasinProfile] = None
    TerminalStatic: Optional[TerminalStatic] = None
    BasinStatic: Optional[BasinStatic] = None
