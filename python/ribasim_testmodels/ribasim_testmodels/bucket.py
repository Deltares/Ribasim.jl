import geopandas as gpd
import numpy as np
import pandas as pd
import ribasim


def bucket_model() -> ribasim.Model:
    """Bucket model with just a single basin."""

    # Set up the nodes:
    xy = np.array(
        [
            (400.0, 200.0),  # Basin
        ]
    )
    node_xy = gpd.points_from_xy(x=xy[:, 0], y=xy[:, 1])
    node_type = ["Basin"]
    # Make sure the feature id starts at 1: explicitly give an index.
    node = ribasim.Node(
        df=gpd.GeoDataFrame(
            data={"node_type": node_type},
            index=pd.Index(np.arange(len(xy)) + 1, name="fid"),
            geometry=node_xy,
            crs="EPSG:28992",
        )
    )

    # Setup the dummy edges:
    from_id = np.array([], dtype=np.int64)
    to_id = np.array([], dtype=np.int64)
    lines = node.geometry_from_connectivity(from_id.tolist(), to_id.tolist())
    edge = ribasim.Edge(
        df=gpd.GeoDataFrame(
            data={
                "from_node_id": from_id,
                "to_node_id": to_id,
                "edge_type": len(from_id) * ["flow"],
            },
            geometry=lines,
            crs="EPSG:28992",
        )
    )

    # Setup the basins:
    profile = pd.DataFrame(
        data={
            "node_id": [1, 1],
            "area": [1000.0, 1000.0],
            "level": [0.0, 1.0],
        }
    )

    state = pd.DataFrame(
        data={
            "node_id": [1],
            "level": [1.0],
        }
    )

    static = pd.DataFrame(
        data={
            "node_id": [1],
            "drainage": [np.nan],
            "potential_evaporation": [np.nan],
            "infiltration": [np.nan],
            "precipitation": [np.nan],
            "urban_runoff": [np.nan],
        }
    )
    basin = ribasim.Basin(profile=profile, static=static, state=state)

    model = ribasim.Model(
        network=ribasim.Network(node=node, edge=edge),
        basin=basin,
        starttime="2020-01-01 00:00:00",
        endtime="2021-01-01 00:00:00",
    )
    return model


def leaky_bucket_model() -> ribasim.Model:
    """Bucket model with dynamic forcing with missings."""

    # Set up the nodes:
    xy = np.array(
        [
            (400.0, 200.0),  # Basin
        ]
    )
    node_xy = gpd.points_from_xy(x=xy[:, 0], y=xy[:, 1])
    node_type = ["Basin"]
    # Make sure the feature id starts at 1: explicitly give an index.
    node = ribasim.Node(
        df=gpd.GeoDataFrame(
            data={"node_type": node_type},
            index=pd.Index(np.arange(len(xy)) + 1, name="fid"),
            geometry=node_xy,
            crs="EPSG:28992",
        )
    )

    # Setup the dummy edges:
    from_id = np.array([], dtype=np.int64)
    to_id = np.array([], dtype=np.int64)
    lines = node.geometry_from_connectivity(from_id.tolist(), to_id.tolist())
    edge = ribasim.Edge(
        df=gpd.GeoDataFrame(
            data={
                "from_node_id": from_id,
                "to_node_id": to_id,
                "edge_type": len(from_id) * ["flow"],
            },
            geometry=lines,
            crs="EPSG:28992",
        )
    )

    # Setup the basins:
    profile = pd.DataFrame(
        data={
            "node_id": [1, 1],
            "area": [1000.0, 1000.0],
            "level": [0.0, 1.0],
        }
    )

    state = pd.DataFrame(
        data={
            "node_id": [1],
            "level": [1.0],
        }
    )

    time = pd.DataFrame(
        data={
            "time": pd.date_range("2020-01-01", "2020-01-05"),
            "node_id": 1,
            "drainage": [0.003, np.nan, 0.001, 0.002, 0.0],
            "potential_evaporation": np.nan,
            "infiltration": [np.nan, 0.001, 0.002, 0.0, 0.0],
            "precipitation": np.nan,
            "urban_runoff": 0.0,
        }
    )
    basin = ribasim.Basin(profile=profile, time=time, state=state)

    model = ribasim.Model(
        network=ribasim.Network(node=node, edge=edge),
        basin=basin,
        starttime="2020-01-01 00:00:00",
        endtime="2020-01-05 00:00:00",
    )
    return model
