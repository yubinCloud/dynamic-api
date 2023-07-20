from typing import TypedDict
from enum import Enum, auto


class ParamFieldType(Enum):
    STRING = auto()
    INTEGER = auto()
    FLOAT = auto()


class ParamFieldInfo(TypedDict):
    """
    SQL 语句中使用 #{} 填充的所有 field 的信息
    """
    name: str
    typed: ParamFieldType


typed_map = {
    'string': ParamFieldType.STRING,
    'str': ParamFieldType.STRING,
    'varchar': ParamFieldType,
    'char': ParamFieldType,
    'int': ParamFieldType.INTEGER,
    'integer': ParamFieldType.INTEGER,
    'float': ParamFieldType.FLOAT,
    'double': ParamFieldType.FLOAT
}