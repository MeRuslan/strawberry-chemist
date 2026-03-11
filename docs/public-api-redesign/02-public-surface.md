# Proposed Public Surface

## Stable Top-Level Exports

Recommended `strawberry_chemist` top-level contract:

```python
import strawberry_chemist as sc
```

Stable exports:

- `type`
- `node`
- `attr`
- `field`
- `relationship`
- `connection`
- `Connection`
- `OffsetConnection` or `OffsetPage`
- `PaginationPolicy`
- `CursorPagination`
- `OffsetPagination`
- `filter`
- `filter_field`
- `FilterContext`
- `FilterSet`
- `manual_filter`
- `StringFilter`
- `IntFilter`
- `FloatFilter`
- `BooleanFilter`
- `IDFilter`
- `DateFilter`
- `DateTimeFilter`
- `order`
- `order_field`
- `OrderContext`
- `manual_order`
- `SortDirection`
- `NullsOrder`
- `Node`
- `node_field`
- `node_lookup`
- `relay`
- `extensions`

## Stable Submodules

Recommended stable submodules:

- `strawberry_chemist.filters`
- `strawberry_chemist.order`
- `strawberry_chemist.relay`
- `strawberry_chemist.pagination`
- `strawberry_chemist.extensions`

## Names To Keep Internal

These should not be presented as the preferred public surface:

- `StrawberrySQLAlchemyField`
- `StrawberrySQLAlchemyRelationField`
- `StrawberrySQLAlchemyFilter`
- `StrawberrySQLAlchemyOrdering`
- `ConnectionLoader`
- `DataLoaderContainer`
- `context_var`
- loading strategies like `ValuesLoadingStrategy` and `UnionLoadingStrategy`

They may remain importable for compatibility or testing, but they should not anchor the docs.

## Current Name -> Proposed Name

| Current | Proposed | Notes |
| --- | --- | --- |
| `field` | `field` + `attr` | split simple mapping from computed field behavior |
| `relation_field` | `relationship` | more explicit and less awkward |
| `relay_connection_field` | `connection` | unify relation/root connection API |
| `limit_offset_connection_field` | `connection(..., pagination=sc.OffsetPagination(...))` | do not expose two separate top-level builders |
| `post_processor` | decorated function body | make transforms feel like normal Python |
| `additional_parent_fields` | `select=[...]` | shorter and clearer |
| `needs_fields` | `select=[...]` on relationships | same mental model |
| `ignore_field_selections` | `load="full"` | user-facing name should describe behavior |
| `RuntimeFilter` | `where=` / `scope=` | SQL-first public naming |
| `StrawberrySQLAlchemyFilter` | `@filter` + `filter_field`, or `manual_filter` when schema shape must stay custom | polished declarative DSL plus explicit manual escape hatch |
| `StrawberrySQLAlchemyOrdering` | `@order` + `order_field`, or `manual_order` when schema shape must stay custom | polished declarative DSL plus explicit manual escape hatch |
| `NodeEdge` | `node_field()` | clearer relay root field story |
| `object_field` / `get_by_id_field` | `node_lookup()` | one stable decorator for loading a node into a resolver |
| `extentions` | `extensions` | spelling fix; remove the typo alias |
| `input()` / `mutation()` | experimental or removed | not mature enough for stable public docs |

## Dedicated Node Decorator

The common relay case should not require:

```python
@sc.type(model=Book, node=...)
class BookNode(sc.Node):
    ...
```

The preferred API should be:

```python
@sc.node(model=Book)
class BookNode:
    ...
```

Rules:

- `@sc.type(model=...)` is for normal non-node types
- `@sc.node(model=...)` is for relay/node types
- `@sc.node(...)` should infer identifier fields by default from the SQLAlchemy mapper primary key
- inheriting from `sc.Node` should be optional or compatibility-only

## What Should Stay Out Of Scope For 1.0

These would bloat the surface before the fundamentals are clean:

- auto-generated CRUD mutations
- fully auto-generated filter and order types without explicit user opt-in
- model registry magic outside relay configuration
- application-specific exception frameworks
- sync + async dual-mode abstractions unless there is a clear use case
