import pandera as pa
from pandera.typing import DataFrame, Series
from pydantic import BaseModel

from ribasim.input_base import InputMixin


class StaticSchema(pa.SchemaModel):
    from_node_id: Series[int] = pa.Field()
    to_node_id: Series[int] = pa.Field()


class Edge(BaseModel, InputMixin):
    _input_type = "Edge"
    static: DataFrame[StaticSchema]
