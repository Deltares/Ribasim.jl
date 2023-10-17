# generated by datamodel-codegen:
#   filename:  root.schema.json

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BasinProfile(BaseModel):
    node_id: int
    area: float
    level: float
    remarks: str = Field("", description="a hack for pandera")


class BasinState(BaseModel):
    node_id: int
    level: float
    remarks: str = Field("", description="a hack for pandera")


class BasinStatic(BaseModel):
    node_id: int
    drainage: float
    potential_evaporation: float
    infiltration: float
    precipitation: float
    urban_runoff: float
    remarks: str = Field("", description="a hack for pandera")


class BasinTime(BaseModel):
    node_id: int
    time: datetime
    drainage: float
    potential_evaporation: float
    infiltration: float
    precipitation: float
    urban_runoff: float
    remarks: str = Field("", description="a hack for pandera")


class DiscreteControlCondition(BaseModel):
    node_id: int
    listen_feature_id: int
    variable: str
    greater_than: float
    look_ahead: Optional[float] = None
    remarks: str = Field("", description="a hack for pandera")


class DiscreteControlLogic(BaseModel):
    node_id: int
    truth_state: str
    control_state: str
    remarks: str = Field("", description="a hack for pandera")


class Edge(BaseModel):
    fid: int
    name: str
    from_node_id: int
    to_node_id: int
    edge_type: str
    remarks: str = Field("", description="a hack for pandera")


class FlowBoundaryStatic(BaseModel):
    node_id: int
    active: Optional[bool] = None
    flow_rate: float
    remarks: str = Field("", description="a hack for pandera")


class FlowBoundaryTime(BaseModel):
    node_id: int
    time: datetime
    flow_rate: float
    remarks: str = Field("", description="a hack for pandera")


class FractionalFlowStatic(BaseModel):
    node_id: int
    fraction: float
    control_state: Optional[str] = None
    remarks: str = Field("", description="a hack for pandera")


class LevelBoundaryStatic(BaseModel):
    node_id: int
    active: Optional[bool] = None
    level: float
    remarks: str = Field("", description="a hack for pandera")


class LevelBoundaryTime(BaseModel):
    node_id: int
    time: datetime
    level: float
    remarks: str = Field("", description="a hack for pandera")


class LevelExporterStatic(BaseModel):
    name: str
    element_id: int
    node_id: int
    basin_level: float
    level: float
    remarks: str = Field("", description="a hack for pandera")


class LinearResistanceStatic(BaseModel):
    node_id: int
    active: Optional[bool] = None
    resistance: float
    control_state: Optional[str] = None
    remarks: str = Field("", description="a hack for pandera")


class ManningResistanceStatic(BaseModel):
    node_id: int
    active: Optional[bool] = None
    length: float
    manning_n: float
    profile_width: float
    profile_slope: float
    control_state: Optional[str] = None
    remarks: str = Field("", description="a hack for pandera")


class Node(BaseModel):
    fid: int
    name: str
    type: str
    remarks: str = Field("", description="a hack for pandera")


class OutletStatic(BaseModel):
    node_id: int
    active: Optional[bool] = None
    flow_rate: float
    min_flow_rate: Optional[float] = None
    max_flow_rate: Optional[float] = None
    min_crest_level: Optional[float] = None
    control_state: Optional[str] = None
    remarks: str = Field("", description="a hack for pandera")


class PidControlStatic(BaseModel):
    node_id: int
    active: Optional[bool] = None
    listen_node_id: int
    target: float
    proportional: float
    integral: float
    derivative: float
    control_state: Optional[str] = None
    remarks: str = Field("", description="a hack for pandera")


class PidControlTime(BaseModel):
    node_id: int
    listen_node_id: int
    time: datetime
    target: float
    proportional: float
    integral: float
    derivative: float
    control_state: Optional[str] = None
    remarks: str = Field("", description="a hack for pandera")


class PumpStatic(BaseModel):
    node_id: int
    active: Optional[bool] = None
    flow_rate: float
    min_flow_rate: Optional[float] = None
    max_flow_rate: Optional[float] = None
    control_state: Optional[str] = None
    remarks: str = Field("", description="a hack for pandera")


class TabulatedRatingCurveStatic(BaseModel):
    node_id: int
    active: Optional[bool] = None
    level: float
    discharge: float
    control_state: Optional[str] = None
    remarks: str = Field("", description="a hack for pandera")


class TabulatedRatingCurveTime(BaseModel):
    node_id: int
    time: datetime
    level: float
    discharge: float
    remarks: str = Field("", description="a hack for pandera")


class TerminalStatic(BaseModel):
    node_id: int
    remarks: str = Field("", description="a hack for pandera")


class UserStatic(BaseModel):
    node_id: int
    active: Optional[bool] = None
    demand: float
    return_factor: float
    min_level: float
    priority: int
    remarks: str = Field("", description="a hack for pandera")


class UserTime(BaseModel):
    node_id: int
    time: datetime
    demand: float
    return_factor: float
    min_level: float
    priority: int
    remarks: str = Field("", description="a hack for pandera")


class Root(BaseModel):
    BasinProfile: Optional[BasinProfile] = None
    BasinState: Optional[BasinState] = None
    BasinStatic: Optional[BasinStatic] = None
    BasinTime: Optional[BasinTime] = None
    DiscreteControlCondition: Optional[DiscreteControlCondition] = None
    DiscreteControlLogic: Optional[DiscreteControlLogic] = None
    Edge: Optional[Edge] = None
    FlowBoundaryStatic: Optional[FlowBoundaryStatic] = None
    FlowBoundaryTime: Optional[FlowBoundaryTime] = None
    FractionalFlowStatic: Optional[FractionalFlowStatic] = None
    LevelBoundaryStatic: Optional[LevelBoundaryStatic] = None
    LevelBoundaryTime: Optional[LevelBoundaryTime] = None
    LevelExporterStatic: Optional[LevelExporterStatic] = None
    LinearResistanceStatic: Optional[LinearResistanceStatic] = None
    ManningResistanceStatic: Optional[ManningResistanceStatic] = None
    Node: Optional[Node] = None
    OutletStatic: Optional[OutletStatic] = None
    PidControlStatic: Optional[PidControlStatic] = None
    PidControlTime: Optional[PidControlTime] = None
    PumpStatic: Optional[PumpStatic] = None
    TabulatedRatingCurveStatic: Optional[TabulatedRatingCurveStatic] = None
    TabulatedRatingCurveTime: Optional[TabulatedRatingCurveTime] = None
    TerminalStatic: Optional[TerminalStatic] = None
    UserStatic: Optional[UserStatic] = None
    UserTime: Optional[UserTime] = None
