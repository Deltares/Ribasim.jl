import numbers
from collections.abc import Sequence
from enum import Enum
from typing import Any, Optional

import numpy as np
import pandas as pd
import pydantic
from geopandas import GeoDataFrame
from pydantic import ConfigDict, Field, NonNegativeInt, model_validator
from shapely.geometry import Point

from ribasim.geometry import BasinAreaSchema, NodeTable
from ribasim.geometry.edge import NodeData
from ribasim.input_base import ChildModel, NodeModel, SpatialTableModel, TableModel

# These schemas are autogenerated
from ribasim.schemas import (
    BasinConcentrationExternalSchema,
    BasinConcentrationSchema,
    BasinConcentrationStateSchema,
    BasinProfileSchema,
    BasinStateSchema,
    BasinStaticSchema,
    BasinSubgridSchema,
    BasinTimeSchema,
    ContinuousControlFunctionSchema,
    ContinuousControlVariableSchema,
    DiscreteControlConditionSchema,
    DiscreteControlLogicSchema,
    DiscreteControlVariableSchema,
    FlowBoundaryConcentrationSchema,
    FlowBoundaryStaticSchema,
    FlowBoundaryTimeSchema,
    FlowDemandStaticSchema,
    FlowDemandTimeSchema,
    LevelBoundaryConcentrationSchema,
    LevelBoundaryStaticSchema,
    LevelBoundaryTimeSchema,
    LevelDemandStaticSchema,
    LevelDemandTimeSchema,
    LinearResistanceStaticSchema,
    ManningResistanceStaticSchema,
    OutletStaticSchema,
    PidControlStaticSchema,
    PidControlTimeSchema,
    PumpStaticSchema,
    TabulatedRatingCurveStaticSchema,
    TabulatedRatingCurveTimeSchema,
    UserDemandStaticSchema,
    UserDemandTimeSchema,
)
from ribasim.utils import _pascal_to_snake


class Allocation(ChildModel):
    """
    Defines the allocation optimization algorithm options.

    Attributes
    ----------
    timestep : float
        The simulated time in seconds between successive allocation calls (Optional, defaults to 86400)
    use_allocation : bool
        Whether the allocation algorithm should be active. If not, `UserDemand` nodes attempt to
        abstract their full demand (Optional, defaults to False)
    """

    timestep: float = 86400.0
    use_allocation: bool = False


class Results(ChildModel):
    outstate: str | None = None
    compression: bool = True
    compression_level: int = 6
    subgrid: bool = False


class Solver(ChildModel):
    """
    Defines the numerical solver options.
    For more details see <https://docs.sciml.ai/DiffEqDocs/stable/basics/common_solver_opts/#solver_options>.

    Attributes
    ----------
    algorithm : str
        The used numerical time integration algorithm (Optional, defaults to QNDF)
    saveat : float
        Time interval in seconds between saves of output data.
        0 saves every timestep, inf only saves at start- and endtime. (Optional, defaults to 86400)
    dt : float
        Timestep of the solver. (Optional, defaults to None which implies adaptive timestepping)
    dtmin : float
        The minimum allowed timestep of the solver (Optional, defaults to 0.0)
    dtmax : float
        The maximum allowed timestep size (Optional, defaults to 0.0 which implies the total length of the simulation)
    force_dtmin : bool
        If a smaller dt than dtmin is needed to meet the set error tolerances, the simulation stops, unless force_dtmin = true
        (Optional, defaults to False)
    abstol : float
        The absolute tolerance for adaptive timestepping (Optional, defaults to 1e-6)
    reltol : float
        The relative tolerance for adaptive timestepping (Optional, defaults to 1e-5)
    maxiters : int
        The total number of linear iterations over the whole simulation. (Defaults to 1e9, only needs to be increased for extremely long simulations)
    sparse : bool
        Whether a sparse Jacobian matrix is used, which gives a significant speedup for models with >~10 basins.
    autodiff : bool
        Whether automatic differentiation instead of fine difference is used to compute the Jacobian. (Optional, defaults to true)
    """

    algorithm: str = "QNDF"
    saveat: float = 86400.0
    dt: float | None = None
    dtmin: float | None = None
    dtmax: float | None = None
    force_dtmin: bool = False
    abstol: float = 1e-06
    reltol: float = 1e-05
    maxiters: int = 1000000000
    sparse: bool = True
    autodiff: bool = True


class Verbosity(str, Enum):
    debug = "debug"
    info = "info"
    warn = "warn"
    error = "error"


class Logging(ChildModel):
    """
    Defines the logging behavior of the core.

    Attributes
    ----------
    verbosity : Verbosity
        The verbosity of the logging: debug/info/warn/error (Optional, defaults to info)
    timing : Bool
        Enable timings (Optional, defaults to False)
    """

    verbosity: Verbosity = Verbosity.info
    timing: bool = False


class Node(pydantic.BaseModel):
    """
    Defines a node for the model.

    Attributes
    ----------
    node_id : Optional[NonNegativeInt]
        Integer ID of the node. Must be unique within the same node type.
    geometry : shapely.geometry.Point
        The coordinates of the node.
    name : str
        An optional name of the node.
    subnetwork_id : int
        Optionally adds this node to a subnetwork, which is input for the allocation algorithm.
    """

    node_id: Optional[NonNegativeInt] = None
    geometry: Point
    name: str = ""
    subnetwork_id: int | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    def __init__(
        self,
        node_id: Optional[NonNegativeInt] = None,
        geometry: Point = Point(0, 0),
        **kwargs,
    ) -> None:
        super().__init__(node_id=node_id, geometry=geometry, **kwargs)

    def into_geodataframe(self, node_type: str, node_id: int) -> GeoDataFrame:
        extra = self.model_extra if self.model_extra is not None else {}
        return GeoDataFrame(
            data={
                "node_id": pd.Series([node_id], dtype=np.int32),
                "node_type": pd.Series([node_type], dtype=str),
                "name": pd.Series([self.name], dtype=str),
                "subnetwork_id": pd.Series([self.subnetwork_id], dtype=pd.Int32Dtype()),
                **extra,
            },
            geometry=[self.geometry],
        )


class MultiNodeModel(NodeModel):
    node: NodeTable = Field(default_factory=NodeTable)
    _node_type: str

    @model_validator(mode="after")
    def filter(self) -> "MultiNodeModel":
        self.node.filter(self.__class__.__name__)
        return self

    def add(
        self, node: Node, tables: Sequence[TableModel[Any]] | None = None
    ) -> NodeData:
        """Add a node and the associated data to the model.

        Parameters
        ----------
        node : Ribasim.Node
        tables : Sequence[TableModel[Any]] | None

        Raises
        ------
        ValueError
            When the given node ID already exists for this node type
        """
        if tables is None:
            tables = []

        node_id = node.node_id

        if node_id is None:
            node_id = self._parent.node_id.new_id()
        elif node_id in self._parent.node_id:
            raise ValueError(
                f"Node IDs have to be unique, but {node_id} already exists."
            )

        for table in tables:
            member_name = _pascal_to_snake(table.__class__.__name__)
            existing_member = getattr(self, member_name)
            existing_table = (
                existing_member.df if existing_member.df is not None else pd.DataFrame()
            )
            assert table.df is not None
            table_to_append = table.df.assign(node_id=node_id)
            setattr(self, member_name, pd.concat([existing_table, table_to_append]))

        node_table = node.into_geodataframe(
            node_type=self.__class__.__name__, node_id=node_id
        )
        self.node.df = (
            node_table
            if self.node.df is None
            else pd.concat([self.node.df, node_table])
        )
        self._parent.node_id.add(node_id)
        return self[node_id]

    def __getitem__(self, index: int) -> NodeData:
        # Unlike TableModel, support only indexing single rows.
        if not isinstance(index, numbers.Integral):
            node_model_name = type(self).__name__
            indextype = type(index).__name__
            raise TypeError(
                f"{node_model_name} index must be an integer, not {indextype}"
            )

        row = self.node[index].iloc[0]
        return NodeData(
            node_id=int(index), node_type=row["node_type"], geometry=row["geometry"]
        )


class Terminal(MultiNodeModel): ...


class PidControl(MultiNodeModel):
    static: TableModel[PidControlStaticSchema] = Field(
        default_factory=TableModel[PidControlStaticSchema],
        json_schema_extra={"sort_keys": ["node_id", "control_state"]},
    )
    time: TableModel[PidControlTimeSchema] = Field(
        default_factory=TableModel[PidControlTimeSchema],
        json_schema_extra={"sort_keys": ["node_id", "time"]},
    )


class LevelBoundary(MultiNodeModel):
    static: TableModel[LevelBoundaryStaticSchema] = Field(
        default_factory=TableModel[LevelBoundaryStaticSchema],
        json_schema_extra={"sort_keys": ["node_id"]},
    )
    time: TableModel[LevelBoundaryTimeSchema] = Field(
        default_factory=TableModel[LevelBoundaryTimeSchema],
        json_schema_extra={"sort_keys": ["node_id", "time"]},
    )
    concentration: TableModel[LevelBoundaryConcentrationSchema] = Field(
        default_factory=TableModel[LevelBoundaryConcentrationSchema],
        json_schema_extra={"sort_keys": ["node_id", "substance", "time"]},
    )


class Pump(MultiNodeModel):
    static: TableModel[PumpStaticSchema] = Field(
        default_factory=TableModel[PumpStaticSchema],
        json_schema_extra={"sort_keys": ["node_id", "control_state"]},
    )


class TabulatedRatingCurve(MultiNodeModel):
    static: TableModel[TabulatedRatingCurveStaticSchema] = Field(
        default_factory=TableModel[TabulatedRatingCurveStaticSchema],
        json_schema_extra={"sort_keys": ["node_id", "control_state", "level"]},
    )
    time: TableModel[TabulatedRatingCurveTimeSchema] = Field(
        default_factory=TableModel[TabulatedRatingCurveTimeSchema],
        json_schema_extra={"sort_keys": ["node_id", "time", "level"]},
    )


class UserDemand(MultiNodeModel):
    static: TableModel[UserDemandStaticSchema] = Field(
        default_factory=TableModel[UserDemandStaticSchema],
        json_schema_extra={"sort_keys": ["node_id", "priority"]},
    )
    time: TableModel[UserDemandTimeSchema] = Field(
        default_factory=TableModel[UserDemandTimeSchema],
        json_schema_extra={"sort_keys": ["node_id", "priority", "time"]},
    )


class LevelDemand(MultiNodeModel):
    static: TableModel[LevelDemandStaticSchema] = Field(
        default_factory=TableModel[LevelDemandStaticSchema],
        json_schema_extra={"sort_keys": ["node_id"]},
    )
    time: TableModel[LevelDemandTimeSchema] = Field(
        default_factory=TableModel[LevelDemandTimeSchema],
        json_schema_extra={"sort_keys": ["node_id", "priority", "time"]},
    )


class FlowBoundary(MultiNodeModel):
    static: TableModel[FlowBoundaryStaticSchema] = Field(
        default_factory=TableModel[FlowBoundaryStaticSchema],
        json_schema_extra={"sort_keys": ["node_id"]},
    )
    time: TableModel[FlowBoundaryTimeSchema] = Field(
        default_factory=TableModel[FlowBoundaryTimeSchema],
        json_schema_extra={"sort_keys": ["node_id", "time"]},
    )
    concentration: TableModel[FlowBoundaryConcentrationSchema] = Field(
        default_factory=TableModel[FlowBoundaryConcentrationSchema],
        json_schema_extra={"sort_keys": ["node_id", "substance", "time"]},
    )


class FlowDemand(MultiNodeModel):
    static: TableModel[FlowDemandStaticSchema] = Field(
        default_factory=TableModel[FlowDemandStaticSchema],
        json_schema_extra={"sort_keys": ["node_id"]},
    )
    time: TableModel[FlowDemandTimeSchema] = Field(
        default_factory=TableModel[FlowDemandTimeSchema],
        json_schema_extra={"sort_keys": ["node_id", "time"]},
    )


class Basin(MultiNodeModel):
    profile: TableModel[BasinProfileSchema] = Field(
        default_factory=TableModel[BasinProfileSchema],
        json_schema_extra={"sort_keys": ["node_id", "level"]},
    )
    state: TableModel[BasinStateSchema] = Field(
        default_factory=TableModel[BasinStateSchema],
        json_schema_extra={"sort_keys": ["node_id"]},
    )
    static: TableModel[BasinStaticSchema] = Field(
        default_factory=TableModel[BasinStaticSchema],
        json_schema_extra={"sort_keys": ["node_id"]},
    )
    time: TableModel[BasinTimeSchema] = Field(
        default_factory=TableModel[BasinTimeSchema],
        json_schema_extra={"sort_keys": ["node_id", "time"]},
    )
    subgrid: TableModel[BasinSubgridSchema] = Field(
        default_factory=TableModel[BasinSubgridSchema],
        json_schema_extra={"sort_keys": ["subgrid_id", "basin_level"]},
    )
    area: SpatialTableModel[BasinAreaSchema] = Field(
        default_factory=SpatialTableModel[BasinAreaSchema],
        json_schema_extra={"sort_keys": ["node_id"]},
    )
    concentration: TableModel[BasinConcentrationSchema] = Field(
        default_factory=TableModel[BasinConcentrationSchema],
        json_schema_extra={"sort_keys": ["node_id", "substance", "time"]},
    )
    concentration_external: TableModel[BasinConcentrationExternalSchema] = Field(
        default_factory=TableModel[BasinConcentrationExternalSchema],
        json_schema_extra={"sort_keys": ["node_id", "substance", "time"]},
    )
    concentration_state: TableModel[BasinConcentrationStateSchema] = Field(
        default_factory=TableModel[BasinConcentrationStateSchema],
        json_schema_extra={"sort_keys": ["node_id", "substance"]},
    )


class ManningResistance(MultiNodeModel):
    static: TableModel[ManningResistanceStaticSchema] = Field(
        default_factory=TableModel[ManningResistanceStaticSchema],
        json_schema_extra={"sort_keys": ["node_id", "control_state"]},
    )


class DiscreteControl(MultiNodeModel):
    variable: TableModel[DiscreteControlVariableSchema] = Field(
        default_factory=TableModel[DiscreteControlVariableSchema],
        json_schema_extra={
            "sort_keys": [
                "node_id",
                "listen_node_id",
                "variable",
            ]
        },
    )
    condition: TableModel[DiscreteControlConditionSchema] = Field(
        default_factory=TableModel[DiscreteControlConditionSchema],
        json_schema_extra={
            "sort_keys": [
                "node_id",
                "compound_variable_id",
                "greater_than",
            ]
        },
    )
    logic: TableModel[DiscreteControlLogicSchema] = Field(
        default_factory=TableModel[DiscreteControlLogicSchema],
        json_schema_extra={"sort_keys": ["node_id", "truth_state"]},
    )


class Outlet(MultiNodeModel):
    static: TableModel[OutletStaticSchema] = Field(
        default_factory=TableModel[OutletStaticSchema],
        json_schema_extra={"sort_keys": ["node_id", "control_state"]},
    )


class LinearResistance(MultiNodeModel):
    static: TableModel[LinearResistanceStaticSchema] = Field(
        default_factory=TableModel[LinearResistanceStaticSchema],
        json_schema_extra={"sort_keys": ["node_id", "control_state"]},
    )


class ContinuousControl(MultiNodeModel):
    variable: TableModel[ContinuousControlVariableSchema] = Field(
        default_factory=TableModel[ContinuousControlVariableSchema],
        json_schema_extra={"sort_keys": ["node_id"]},
    )
    function: TableModel[ContinuousControlFunctionSchema] = Field(
        default_factory=TableModel[ContinuousControlFunctionSchema],
        json_schema_extra={"sort_keys": ["node_id", "input"]},
    )
