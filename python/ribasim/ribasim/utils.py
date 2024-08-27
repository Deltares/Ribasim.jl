import re

import numpy as np
import pandas as pd
from pandera.dtypes import Int32
from pandera.typing import Series
from pydantic import BaseModel, NonNegativeInt


def _pascal_to_snake(pascal_str):
    # Insert a '_' before all uppercase letters that are not at the start of the string
    # and convert the string to lowercase
    return re.sub(r"(?<!^)(?=[A-Z])", "_", pascal_str).lower()


class MissingOptionalModule:
    """Presents a clear error for optional modules."""

    def __init__(self, name, suggestion="all"):
        self.name = name
        self.suggestion = suggestion

    def __getattr__(
        self,
        _,
    ):
        raise ImportError(
            f"{self.name} is required for this functionality. You can get it using `pip install ribasim[{self.suggestion}]`."
        )


def _node_lookup_numpy(node_id) -> Series[Int32]:
    """Create a lookup table from from node_id to the node dimension index.
    Used when adding data onto the nodes of an xugrid dataset.
    """
    return pd.Series(
        index=node_id,
        data=node_id.argsort().astype(np.int32),
        name="node_index",
    )


def _node_lookup(uds) -> Series[Int32]:
    """Create a lookup table from from node_id to the node dimension index.
    Used when adding data onto the nodes of an xugrid dataset.
    """
    return pd.Series(
        index=uds["node_id"],
        data=uds[uds.grid.node_dimension],
        name="node_index",
    )


def _edge_lookup(uds) -> Series[Int32]:
    """Create a lookup table from edge_id to the edge dimension index.

    Used when adding data onto the edges of an xugrid dataset.
    """

    return pd.Series(
        index=uds["edge_id"],
        data=uds[uds.grid.edge_dimension],
        name="edge_index",
    )


def _time_in_ns(df) -> None:
    """Convert the time column to datetime64[ns] dtype."""
    # datetime64[ms] gives trouble; https://github.com/pydata/xarray/issues/6318
    df["time"] = df["time"].astype("datetime64[ns]")


class UsedIDs(BaseModel):
    """A helper class to manage globally unique node IDs.

    We keep track of all IDs in the model,
    and keep track of the maximum to provide new IDs.
    MultiNodeModels and Edge will check this instance on `add`.
    """

    node_ids: set[int] = set()
    max_node_id: NonNegativeInt = 0

    def add(self, node_id: int) -> None:
        self.node_ids.add(node_id)
        self.max_node_id = max(self.max_node_id, node_id)

    def __contains__(self, value: int) -> bool:
        return self.node_ids.__contains__(value)

    def new_id(self) -> int:
        return self.max_node_id + 1
