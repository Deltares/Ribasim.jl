import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Generator
from contextlib import closing
from contextvars import ContextVar
from pathlib import Path
from sqlite3 import Connection, connect
from typing import (
    Any,
    Generic,
    TypeVar,
    cast,
)

import geopandas as gpd
import numpy as np
import pandas as pd
import pandera as pa
from pandera.typing import DataFrame
from pandera.typing.geopandas import GeoDataFrame
from pydantic import BaseModel as PydanticBaseModel
from pydantic import (
    ConfigDict,
    DirectoryPath,
    Field,
    PrivateAttr,
    ValidationInfo,
    field_validator,
    model_serializer,
    model_validator,
    validate_call,
)

import ribasim

from .styles import _add_styles_to_geopackage

__all__ = ("TableModel",)

delimiter = " / "
node_names_snake_case = [
    "basin",
    "continuous_control",
    "discrete_control",
    "flow_boundary",
    "flow_demand",
    "level_boundary",
    "level_demand",
    "linear_resistance",
    "manning_resistance",
    "outlet",
    "pid_control",
    "pump",
    "tabulated_rating_curve",
    "user_demand",
]

gpd.options.io_engine = "pyogrio"

context_file_loading: ContextVar[dict[str, Any]] = ContextVar(
    "file_loading", default={}
)

TableT = TypeVar("TableT", bound=pa.DataFrameModel)


def esc_id(identifier: str) -> str:
    """Escape SQLite identifiers."""
    return '"' + identifier.replace('"', '""') + '"'


def exists(connection: Connection, name: str) -> bool:
    """Check if a table exists in a SQLite database."""
    with closing(connection.cursor()) as cursor:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
        )
        result = cursor.fetchone()
    return result is not None


TABLES = ["profile", "state", "static", "time", "logic", "condition"]


class BaseModel(PydanticBaseModel):
    """Overrides Pydantic BaseModel to set our own config."""

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        populate_by_name=True,
        use_enum_values=True,
        extra="allow",
    )

    @classmethod
    def _fields(cls) -> list[str]:
        """Return the names of the fields contained in the Model."""
        return list(cls.model_fields.keys())


class FileModel(BaseModel, ABC):
    """Base class to represent models with a file representation.

    It therefore always has a `filepath` and if it is given on
    initialization, it will parse that file.

    This class extends the `model_validator` option of Pydantic,
    so when when a Path is given to a field with type `FileModel`,
    it doesn't error, but actually initializes the `FileModel`.

    Attributes
    ----------
        filepath (Path | None):
            The path of this FileModel.
    """

    filepath: Path | None = Field(default=None, exclude=True, repr=False)

    @model_validator(mode="before")
    @classmethod
    def _check_filepath(cls, value: Any) -> Any:
        # Enable initialization with a Path.
        if isinstance(value, dict):
            # Pydantic Model init requires a dict
            filepath = value.get("filepath", None)
            if filepath is not None:
                filepath = Path(filepath)
            data = cls._load(filepath)
            data.update(value)
            return data
        elif isinstance(value, Path | str):
            # Pydantic Model init requires a dict
            data = cls._load(Path(value))
            data["filepath"] = value
            return data
        else:
            return value

    @validate_call
    def set_filepath(self, filepath: Path) -> None:
        """Set the filepath of this instance.

        Args:
            filepath (Path): The filepath to set.
        """
        # Disable assignment validation, which would
        # otherwise trigger check_filepath() and _load() again.
        self.model_config["validate_assignment"] = False
        self.filepath = filepath
        self.model_config["validate_assignment"] = True

    @classmethod
    @abstractmethod
    def _load(cls, filepath: Path | None) -> dict[str, Any]:
        """Load the data at filepath and returns it as a dictionary.

        If a derived FileModel does not load data from disk, this should
        return an empty dictionary.

        Args
        ----
            filepath (Path): Path to the data to load.

        Returns
        -------
            dict: The data stored at filepath
        """
        raise NotImplementedError()


class TableModel(FileModel, Generic[TableT]):
    df: DataFrame[TableT] | None = Field(default=None, exclude=True, repr=False)
    _sort_keys: list[str] = PrivateAttr(default=[])

    @field_validator("df")
    @classmethod
    def _check_extra_columns(cls, v: DataFrame[TableT]):
        """Allow only extra columns with `meta_` prefix."""
        if isinstance(v, (pd.DataFrame, gpd.GeoDataFrame)):
            for colname in v.columns:
                if colname == "fid":
                    # Autogenerated on writing, don't carry them
                    v = v.drop(columns=["fid"])
                elif colname not in cls.columns() and not colname.startswith("meta_"):
                    raise ValueError(
                        f"Unrecognized column '{colname}'. Extra columns need a 'meta_' prefix."
                    )
        return v

    @model_serializer
    def _set_model(self) -> str | None:
        return str(self.filepath.name) if self.filepath is not None else None

    @classmethod
    def tablename(cls) -> str:
        """Retrieve tablename based on attached Schema.

        NodeSchema -> Schema
        TabularRatingCurveStaticSchema -> TabularRatingCurve / Static
        """
        cls_string = str(cls.tableschema())
        names: list[str] = re.sub("([A-Z]+)", r" \1", cls_string).split()[:-1]
        names_lowered = [name.lower() for name in names]
        if len(names) == 1:
            return names[0]
        else:
            for n in range(1, len(names_lowered) + 1):
                node_name_snake_case = "_".join(names_lowered[:n])
                if node_name_snake_case in node_names_snake_case:
                    node_name = "".join(names[:n])
                    table_name = "_".join(names_lowered[n:])
                    return node_name + delimiter + table_name
            raise ValueError(f"Found no known node name in {cls_string}")

    @model_validator(mode="before")
    @classmethod
    def _check_dataframe(cls, value: Any) -> Any:
        # Enable initialization with a DataFrame.
        if isinstance(value, pd.DataFrame | gpd.GeoDataFrame):
            value = {"df": value}

        return value

    def _node_ids(self) -> set[int]:
        node_ids: set[int] = set()
        if self.df is not None and "node_id" in self.df.columns:
            node_ids.update(self.df["node_id"])

        return node_ids

    @classmethod
    def _load(cls, filepath: Path | None) -> dict[str, Any]:
        db = context_file_loading.get().get("database")
        if filepath is not None:
            adf = cls._from_arrow(filepath)
            # TODO Store filepath?
            return {"df": adf}
        elif db is not None:
            ddf = cls._from_db(db, cls.tablename())
            return {"df": ddf}
        else:
            return {}

    def _save(self, directory: DirectoryPath, input_dir: DirectoryPath) -> None:
        # TODO directory could be used to save an arrow file
        db_path = context_file_loading.get().get("database")
        if self.filepath is not None:
            self.sort()
            self._write_arrow(self.filepath, directory, input_dir)
        elif db_path is not None:
            self.sort()
            self._write_geopackage(db_path)

    def _write_geopackage(self, temp_path: Path) -> None:
        """
        Write the contents of the input to a database.

        Parameters
        ----------
        connection : Connection
            SQLite connection to the database.
        """
        assert self.df is not None
        table = self.tablename()

        # Add `fid` to all tables as primary key
        # Enables editing values manually in QGIS
        df = self.df.copy()
        df["fid"] = range(1, len(df) + 1)

        with closing(connect(temp_path)) as connection:
            df.to_sql(
                table,
                connection,
                index=False,
                if_exists="replace",
                dtype={"fid": "INTEGER PRIMARY KEY AUTOINCREMENT"},
            )

            # Set geopackage attribute table
            with closing(connection.cursor()) as cursor:
                sql = "INSERT INTO gpkg_contents (table_name, data_type, identifier) VALUES (?, ?, ?)"
                cursor.execute(sql, (table, "attributes", table))
            connection.commit()

    def _write_arrow(self, filepath: Path, directory: Path, input_dir: Path) -> None:
        """Write the contents of the input to a an arrow file."""
        assert self.df is not None
        path = directory / input_dir / filepath
        path.parent.mkdir(parents=True, exist_ok=True)
        self.df.to_feather(
            path,
            compression="zstd",
            compression_level=6,
        )

    @classmethod
    def _from_db(cls, path: Path, table: str) -> pd.DataFrame | None:
        with connect(path) as connection:
            if exists(connection, table):
                query = f"select * from {esc_id(table)}"
                df = pd.read_sql_query(
                    query, connection, parse_dates={"time": {"format": "ISO8601"}}
                )
            else:
                df = None

            return df

    @classmethod
    def _from_arrow(cls, path: Path) -> pd.DataFrame:
        directory = context_file_loading.get().get("directory", Path("."))
        return pd.read_feather(directory / path)

    def sort(self):
        """Sort the table as required.

        Sorting is done automatically before writing the table.
        """
        if self.df is not None:
            self.df.sort_values(self._sort_keys, ignore_index=True, inplace=True)

    @classmethod
    def tableschema(cls) -> TableT:
        """Retrieve Pandera Schema.

        The type of the field `df` is known to always be an DataFrame[TableT]]] | None
        """
        optionalfieldtype = cls.model_fields["df"].annotation
        fieldtype = optionalfieldtype.__args__[0]  # type: ignore
        T: TableT = fieldtype.__args__[0]
        return T

    @classmethod
    def columns(cls) -> list[str]:
        """Retrieve column names."""
        T = cls.tableschema()
        return list(T.to_schema().columns.keys())

    def __repr__(self) -> str:
        # Make sure not to return just "None", because it gets extremely confusing
        # when debugging.
        return f"{self.tablename()}\n{self.df.__repr__()}"

    def _repr_html_(self):
        if self.df is None:
            return self.__repr__()
        else:
            return f"<div>{self.tablename()}</div>" + self.df._repr_html_()

    def __getitem__(self, index) -> pd.DataFrame | gpd.GeoDataFrame:
        tablename = self.tablename()
        if self.df is None:
            raise ValueError(f"Cannot index into {tablename}: it contains no data.")

        # Allow for indexing with multiple values.
        np_index = np.atleast_1d(index)
        missing = np.setdiff1d(np_index, self.df["node_id"].unique())
        if missing.size > 0:
            raise IndexError(f"{tablename} does not contain node_id: {missing}")

        # Index with .loc[..., :] to always return a DataFrame.
        return self.df.loc[self.df["node_id"].isin(np_index), :]


class SpatialTableModel(TableModel[TableT], Generic[TableT]):
    df: GeoDataFrame[TableT] | None = Field(default=None, exclude=True, repr=False)

    @classmethod
    def _from_db(cls, path: Path, table: str):
        with connect(path) as connection:
            if exists(connection, table):
                df = gpd.read_file(path, layer=table, fid_as_index=True)
            else:
                df = None

            return df

    def _write_geopackage(self, path: Path) -> None:
        """
        Write the contents of the input to the GeoPackage.

        Parameters
        ----------
        path : Path
        """
        assert self.df is not None
        # the index name must be fid otherwise it will generate a separate fid column
        self.df.index.name = "fid"
        self.df.to_file(path, layer=self.tablename(), index=True, driver="GPKG")
        _add_styles_to_geopackage(path, self.tablename())


class ChildModel(BaseModel):
    _parent: Any | None = None
    _parent_field: str | None = None

    @model_validator(mode="after")
    def _check_parent(self) -> "ChildModel":
        if self._parent is not None:
            self._parent.model_fields_set.update({self._parent_field})
        return self


class NodeModel(ChildModel):
    """Base class to handle combining the tables for a single node type."""

    @model_serializer(mode="wrap")
    def set_modeld(
        self, serializer: Callable[[type["NodeModel"]], dict[str, Any]]
    ) -> dict[str, Any]:
        content = serializer(self)
        return dict(filter(lambda x: x[1], content.items()))

    @field_validator("*")
    @classmethod
    def set_sort_keys(cls, v: Any, info: ValidationInfo) -> Any:
        """Set sort keys for all TableModels if present in FieldInfo."""
        if isinstance(v, (TableModel,)):
            field = cls.model_fields[getattr(info, "field_name")]
            extra = field.json_schema_extra
            if extra is not None and isinstance(extra, dict):
                # We set sort_keys ourselves as list[str] in json_schema_extra
                # but mypy doesn't know.
                v._sort_keys = cast(list[str], extra.get("sort_keys", []))
        return v

    @classmethod
    def get_input_type(cls):
        return cls.__name__

    @classmethod
    def _layername(cls, field: str) -> str:
        return f"{cls.get_input_type()}{delimiter}{field}"

    def _tables(self) -> Generator[TableModel[Any], Any, None]:
        for key in self._fields():
            attr = getattr(self, key)
            if (
                isinstance(attr, TableModel)
                and (attr.df is not None)
                and not (isinstance(attr, ribasim.geometry.node.NodeTable))
            ):
                yield attr

    def _node_ids(self) -> set[int]:
        node_ids: set[int] = set()
        for table in self._tables():
            node_ids.update(table._node_ids())
        return node_ids

    def _save(self, directory: DirectoryPath, input_dir: DirectoryPath):
        for table in self._tables():
            table._save(directory, input_dir)

    def _repr_content(self) -> str:
        """Generate a succinct overview of the content.

        Skip "empty" attributes: when the dataframe of a TableModel is None.
        """
        content = []
        for field in self._fields():
            attr = getattr(self, field)
            if isinstance(attr, TableModel):
                if attr.df is not None:
                    content.append(field)
            else:
                content.append(field)
        return ", ".join(content)

    def __repr__(self) -> str:
        content = self._repr_content()
        typename = type(self).__name__
        return f"{typename}({content})"
