from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.sql import Select


@dataclass
class QueryBuildContext:
    model: type
    info: Any = None
    node_type: Any = None
    joins: set[str] = field(default_factory=set)

    def resolve_path(self, stmt: Select, path: str) -> tuple[Select, Any]:
        return resolve_model_path(
            stmt,
            self.model,
            path,
            joins=self.joins,
        )


def infer_model_from_query(stmt: Select) -> type:
    for description in stmt.column_descriptions:
        entity = description.get("entity")
        if entity is not None:
            return entity
    raise ValueError("Could not infer SQLAlchemy model from query")


def resolve_model_path(
    stmt: Select,
    model: type,
    path: str,
    joins: Optional[set[str]] = None,
) -> tuple[Select, Any]:
    joins = joins if joins is not None else set()
    if "." not in path:
        return stmt, getattr(model, path)

    current_model = model
    parts = path.split(".")
    traversed: list[str] = []
    for relation_name in parts[:-1]:
        traversed.append(relation_name)
        join_key = ".".join(traversed)
        relation = getattr(current_model, relation_name)
        if join_key not in joins:
            stmt = stmt.outerjoin(relation)
            joins.add(join_key)
        current_model = relation.property.mapper.class_

    return stmt, getattr(current_model, parts[-1])
