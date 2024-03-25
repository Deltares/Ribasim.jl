from typing import Any

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandera as pa
from matplotlib.patches import Patch
from pandera.typing import Series
from pandera.typing.geopandas import GeoSeries

from ribasim.input_base import SpatialTableModel

__all__ = ("NodeTable",)


class NodeSchema(pa.SchemaModel):
    node_id: Series[np.int32]
    name: Series[str] = pa.Field(default="")
    node_type: Series[str] = pa.Field(default="")
    subnetwork_id: Series[pd.Int32Dtype] = pa.Field(
        default=pd.NA, nullable=True, coerce=True
    )
    geometry: GeoSeries[Any] = pa.Field(default=None, nullable=True)

    class Config:
        add_missing_columns = True
        coerce = True


class NodeTable(SpatialTableModel[NodeSchema]):
    """The Ribasim nodes as Point geometries."""

    def filter(self, nodetype: str):
        """Filter the node table based on the node type."""
        if self.df is not None:
            mask = self.df[self.df["node_type"] != nodetype].index
            self.df.drop(mask, inplace=True)
            self.df.reset_index(inplace=True, drop=True)

    def sort(self):
        assert self.df is not None
        sort_keys = ["node_type", "node_id"]
        self.df.sort_values(sort_keys, ignore_index=True, inplace=True)

    def plot_allocation_networks(self, ax=None, zorder=None) -> Any:
        if ax is None:
            _, ax = plt.subplots()
            ax.axis("off")

        COLOR_SUBNETWORK = "black"
        COLOR_MAIN_NETWORK = "blue"
        ALPHA = 0.25

        contains_main_network = False
        contains_subnetworks = False
        assert self.df is not None

        for subnetwork_id, df_subnetwork in self.df.groupby("subnetwork_id"):
            if subnetwork_id is None:
                continue
            elif subnetwork_id == 1:
                contains_main_network = True
                color = COLOR_MAIN_NETWORK
            else:
                contains_subnetworks = True
                color = COLOR_SUBNETWORK

            hull = gpd.GeoDataFrame(
                geometry=[df_subnetwork.geometry.unary_union.convex_hull]
            )
            hull.plot(ax=ax, color=color, alpha=ALPHA, zorder=zorder)

        handles = []
        labels = []

        if contains_main_network:
            handles.append(Patch(facecolor=COLOR_MAIN_NETWORK, alpha=ALPHA))
            labels.append("Main network")
        if contains_subnetworks:
            handles.append(Patch(facecolor=COLOR_SUBNETWORK, alpha=ALPHA))
            labels.append("Subnetwork")

        return handles, labels

    def plot(self, ax=None, zorder=None) -> Any:
        """
        Plot the nodes. Each node type is given a separate marker.

        Parameters
        ----------
        ax : Optional
            The axis on which the nodes will be plotted.

        Returns
        -------
        None
        """
        if ax is None:
            _, ax = plt.subplots()
            ax.axis("off")

        MARKERS = {
            "Basin": "o",
            "FractionalFlow": "^",
            "LevelBoundary": "o",
            "LinearResistance": "^",
            "ManningResistance": "D",
            "TabulatedRatingCurve": "D",
            "Pump": "h",
            "Outlet": "h",
            "Terminal": "s",
            "FlowBoundary": "h",
            "DiscreteControl": "*",
            "PidControl": "x",
            "UserDemand": "s",
            "LevelDemand": "o",
            "FlowDemand": "h",
            "": "o",
        }

        COLORS = {
            "Basin": "b",
            "FractionalFlow": "r",
            "LevelBoundary": "g",
            "LinearResistance": "g",
            "ManningResistance": "r",
            "TabulatedRatingCurve": "g",
            "Pump": "0.5",  # grayscale level
            "Outlet": "g",
            "Terminal": "m",
            "FlowBoundary": "m",
            "DiscreteControl": "k",
            "PidControl": "k",
            "UserDemand": "g",
            "LevelDemand": "k",
            "FlowDemand": "r",
            "": "k",
        }
        if self.df is None:
            return

        for nodetype, df in self.df.groupby("node_type"):
            assert isinstance(nodetype, str)
            marker = MARKERS[nodetype]
            color = COLORS[nodetype]
            ax.scatter(
                df.geometry.x,
                df.geometry.y,
                marker=marker,
                color=color,
                zorder=zorder,
                label=nodetype,
            )

        assert self.df is not None
        geometry = self.df["geometry"]
        for text, xy in zip(
            self.df["node_id"], np.column_stack((geometry.x, geometry.y))
        ):
            ax.annotate(text=text, xy=xy, xytext=(2.0, 2.0), textcoords="offset points")

        return ax
