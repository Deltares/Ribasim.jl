# generated by datamodel-codegen:
#   filename:  root.schema.json

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ribasim.input_base import BaseModel


class AllocationLevelControlStatic(BaseModel):
    node_id: int
    min_level: float
    max_level: float
    priority: int
    remarks: str = Field("", description="a hack for pandera")


class AllocationLevelControlTime(BaseModel):
    node_id: int
    time: datetime
    min_level: float
    max_level: float
    priority: int
    remarks: str = Field("", description="a hack for pandera")


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
    drainage: float | None = None
    potential_evaporation: float | None = None
    infiltration: float | None = None
    precipitation: float | None = None
    urban_runoff: float | None = None
    remarks: str = Field("", description="a hack for pandera")


class BasinSubgrid(BaseModel):
    subgrid_id: int
    node_id: int
    basin_level: float
    subgrid_level: float
    remarks: str = Field("", description="a hack for pandera")


class BasinTime(BaseModel):
    node_id: int
    time: datetime
    drainage: float | None = None
    potential_evaporation: float | None = None
    infiltration: float | None = None
    precipitation: float | None = None
    urban_runoff: float | None = None
    remarks: str = Field("", description="a hack for pandera")


class DiscreteControlCondition(BaseModel):
    node_id: int
    listen_feature_id: int
    variable: str
    greater_than: float
    look_ahead: float | None = None
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
    allocation_network_id: int | None = None
    remarks: str = Field("", description="a hack for pandera")


class FlowBoundaryStatic(BaseModel):
    node_id: int
    active: bool | None = None
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
    control_state: str | None = None
    remarks: str = Field("", description="a hack for pandera")


class LevelBoundaryStatic(BaseModel):
    node_id: int
    active: bool | None = None
    level: float
    remarks: str = Field("", description="a hack for pandera")


class LevelBoundaryTime(BaseModel):
    node_id: int
    time: datetime
    level: float
    remarks: str = Field("", description="a hack for pandera")


class LinearResistanceStatic(BaseModel):
    node_id: int
    active: bool | None = None
    resistance: float
    control_state: str | None = None
    remarks: str = Field("", description="a hack for pandera")


class ManningResistanceStatic(BaseModel):
    node_id: int
    active: bool | None = None
    length: float
    manning_n: float
    profile_width: float
    profile_slope: float
    control_state: str | None = None
    remarks: str = Field("", description="a hack for pandera")


class Node(BaseModel):
    fid: int
    name: str
    type: str
    allocation_network_id: int | None = None
    remarks: str = Field("", description="a hack for pandera")


class OutletStatic(BaseModel):
    node_id: int
    active: bool | None = None
    flow_rate: float
    min_flow_rate: float | None = None
    max_flow_rate: float | None = None
    min_crest_level: float | None = None
    control_state: str | None = None
    remarks: str = Field("", description="a hack for pandera")


class PidControlStatic(BaseModel):
    node_id: int
    active: bool | None = None
    listen_node_id: int
    target: float
    proportional: float
    integral: float
    derivative: float
    control_state: str | None = None
    remarks: str = Field("", description="a hack for pandera")


class PidControlTime(BaseModel):
    node_id: int
    listen_node_id: int
    time: datetime
    target: float
    proportional: float
    integral: float
    derivative: float
    control_state: str | None = None
    remarks: str = Field("", description="a hack for pandera")


class PumpStatic(BaseModel):
    node_id: int
    active: bool | None = None
    flow_rate: float
    min_flow_rate: float | None = None
    max_flow_rate: float | None = None
    control_state: str | None = None
    remarks: str = Field("", description="a hack for pandera")


class TabulatedRatingCurveStatic(BaseModel):
    node_id: int
    active: bool | None = None
    level: float
    flow_rate: float
    control_state: str | None = None
    remarks: str = Field("", description="a hack for pandera")


class TabulatedRatingCurveTime(BaseModel):
    node_id: int
    time: datetime
    level: float
    flow_rate: float
    remarks: str = Field("", description="a hack for pandera")


class TerminalStatic(BaseModel):
    node_id: int
    remarks: str = Field("", description="a hack for pandera")


class UserStatic(BaseModel):
    node_id: int
    active: bool | None = None
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
    allocationlevelcontrolstatic: AllocationLevelControlStatic | None = None
    allocationlevelcontroltime: AllocationLevelControlTime | None = None
    basinprofile: BasinProfile | None = None
    basinstate: BasinState | None = None
    basinstatic: BasinStatic | None = None
    basinsubgrid: BasinSubgrid | None = None
    basintime: BasinTime | None = None
    discretecontrolcondition: DiscreteControlCondition | None = None
    discretecontrollogic: DiscreteControlLogic | None = None
    edge: Edge | None = None
    flowboundarystatic: FlowBoundaryStatic | None = None
    flowboundarytime: FlowBoundaryTime | None = None
    fractionalflowstatic: FractionalFlowStatic | None = None
    levelboundarystatic: LevelBoundaryStatic | None = None
    levelboundarytime: LevelBoundaryTime | None = None
    linearresistancestatic: LinearResistanceStatic | None = None
    manningresistancestatic: ManningResistanceStatic | None = None
    node: Node | None = None
    outletstatic: OutletStatic | None = None
    pidcontrolstatic: PidControlStatic | None = None
    pidcontroltime: PidControlTime | None = None
    pumpstatic: PumpStatic | None = None
    tabulatedratingcurvestatic: TabulatedRatingCurveStatic | None = None
    tabulatedratingcurvetime: TabulatedRatingCurveTime | None = None
    terminalstatic: TerminalStatic | None = None
    userstatic: UserStatic | None = None
    usertime: UserTime | None = None
