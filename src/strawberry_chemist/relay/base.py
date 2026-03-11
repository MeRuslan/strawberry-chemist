import logging
import warnings
from functools import lru_cache
from typing import Dict, List, Type, Any, Union, Awaitable, Optional, TypeVar

import strawberry
from bidict import MutableBidict, frozenbidict
from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument
from strawberry.field import StrawberryField
from strawberry.types import Info

import strawberry_chemist
from strawberry_chemist.gql_context import SQLAlchemyContext
from strawberry_chemist.relay.alphabet_manipilations import (
    base_alphabet_to_10,
    base_10_to_alphabet,
    LOWERCASE_CONVERSION_DATA,
    URL_CONVERSION_DATA,
)
from strawberry_chemist.relay.szudzik_int_bijection import (
    elegant_pair,
    elegant_unpair,
)

sqla_model_registry: Optional[frozenbidict] = None

__magic_number = 5713747


T = TypeVar("T")
logger = logging.getLogger(__name__)


def get_all_subclasses(cls) -> List[Type]:
    all_subclasses = []

    for subclass in cls.__subclasses__():
        if subclass == cls:
            continue
        all_subclasses.append(subclass)
        all_subclasses.extend(get_all_subclasses(subclass))

    return all_subclasses


@lru_cache(maxsize=1)
def node_type_to_int_bijection() -> frozenbidict:
    sub_cls = get_all_subclasses(Node)
    global sqla_model_registry
    bi_dict = MutableBidict(sqla_model_registry or {})
    for cls in sub_cls:
        if not hasattr(cls, "_container_type"):
            continue

        sqla_model = cls._container_type.model
        if sqla_model in bi_dict.inverse:
            # already provided
            continue

        if hasattr(sqla_model, "__int_identity__"):
            key = sqla_model.__int_identity__
        else:
            faulty_chars = [
                s
                for s in sqla_model.__name__.lower()
                if s not in LOWERCASE_CONVERSION_DATA.ALPHABET
            ]
            if faulty_chars:
                warnings.warn(
                    message=f"sqlalchemy type {sqla_model} has a name that "
                    f"contains characters not in the conversion dict: {faulty_chars}"
                    f"please consider renaming the type, or resolving otherwise:"
                    f" LIMITATIONS.md#model-names",
                    category=UserWarning,
                )
            key = base_alphabet_to_10(
                sqla_model.__name__.lower(), LOWERCASE_CONVERSION_DATA
            )

        if key in bi_dict and bi_dict[key] != sqla_model:
            raise ValueError(
                f"{key} type already in registry, due to duplicate name;"
                f" maybe rename sqlalchemy type {sqla_model}"
            )
        elif key not in bi_dict:
            logger.debug(
                f"ID generation: adding generated bidirectional mapping"
                f" key <> model: [{key} <> {sqla_model}]",
            )
            bi_dict[key] = sqla_model

    sqla_model_registry = frozenbidict(bi_dict)

    return sqla_model_registry


def parse_id(id: strawberry.ID | str) -> (Type, int):
    exc = ValueError(f"no node with id: {id}")
    if not id:
        raise exc
    try:
        id = base_alphabet_to_10(id, URL_CONVERSION_DATA)
    except:
        raise exc
    id = id ^ __magic_number
    cls_int, id_int = elegant_unpair(id)

    biject = node_type_to_int_bijection()
    if cls_int not in biject.keys():
        raise exc
    cls = biject[cls_int]
    try:
        real_id = int(id_int)
    except ValueError:
        raise exc

    return cls, real_id


def parse_and_validate_id(
    id: strawberry.ID | str,
    model: Type,
) -> Optional[int]:
    try:
        cls, id_ = parse_id(id)
        if not issubclass(cls, model) and cls != model:
            return None
        return id_
    except ValueError:
        return None


def compose_id_using_instance(
    source: Any, value: Optional[int] = None
) -> strawberry.ID:
    # info.get('me')
    if value is None:
        value = source.id

    biject = node_type_to_int_bijection()

    type_int = biject.inverse[type(source)]
    id_int = value
    common_int = elegant_pair(type_int, id_int)
    common_int = common_int ^ __magic_number
    return strawberry.ID(base_10_to_alphabet(common_int, URL_CONVERSION_DATA))


def maybe_compose_id(source: Any, value: Optional[int]) -> Optional[strawberry.ID]:
    if value is None:
        return None
    return compose_id_using_instance(source, value)


def compose_id_using_class(source_type: Type, value: int) -> strawberry.ID:
    # info.get('me')
    biject = node_type_to_int_bijection()

    type_int = biject.inverse[source_type]
    id_int = value
    common_int = elegant_pair(type_int, id_int)
    common_int = common_int ^ __magic_number
    return strawberry.ID(base_10_to_alphabet(common_int, URL_CONVERSION_DATA))


@strawberry.interface
class Node:
    id: strawberry.ID = strawberry_chemist.field(
        post_processor=compose_id_using_instance
    )


class _RelayNodeField(StrawberryField):
    @property
    def arguments(self) -> List[StrawberryArgument]:
        return [
            StrawberryArgument(
                python_name="id",
                graphql_name="id",
                type_annotation=StrawberryAnnotation(strawberry.ID),
            )
        ]

    @property
    def is_basic_field(self) -> bool:
        return False

    async def get_result(
        self,
        source: Any,
        info: Info[SQLAlchemyContext, Any],
        args: List[Any],
        kwargs: Dict[str, Any],
    ) -> Union[Awaitable[Any], Any]:
        id = kwargs.get("id")
        try:
            model, id = parse_id(id)
        except ValueError:
            raise ValueError("Node not found")
        async with info.context.get_session() as session:
            res = await session.execute(select(model).where(model.id == id))
            res = res.scalars().one_or_none()
        return res


# def delete_by_id(_func=None, *, model=Any, condition=RuntimeFilter, strawberry_args=None):
#     def decorator_action_on_node(func):
#         async def wrapper_action_on_node(self, node: Any, info: Info):
#             async with info.context.get_session() as session:
#                 async with session.begin():
#                     stmt = select(model).where(
#                         ()
#                         & (MediaConsumptionState.library_entity_id == node.id)
#                     )
#                     cons_state = (await session.execute(stmt)).scalar_one_or_none()
#                     if cons_state:
#                         await session.delete(cons_state)
#
#             return await func(self, node=node, info=info)
#
#     return decorator_action_on_node(get_by_id_field(_func))


def get_by_id_field(
    _func=None,
    *,
    allowed_models=Any,
    strawberry_args=None,
    id_nullable=False,
):
    """
    Wrapper that returns you a strawberry field that fetches a node of specified type

    :param _func: allows for calling decorator with or without additional params
                must accept 3 args, of them 2 are passed as keyword args: {node, info}
    :param allowed_models: models to accept for the field
    :param strawberry_args: args to pass to strawberry.field(...), e.g. permission_classes
    :return: the original function wrapped in a strawberry.field,
                with a single input parameter - id: strawberry.ID
                and the output annotation of the original function
    """

    def decorator_action_on_node(func):
        async def wrapper_action_on_node(self, id: strawberry.ID, info: Info):
            try:
                model, id_ = parse_id(id)
            except ValueError:
                model = None
            # Find out if the model conforms
            if allowed_models == Any:
                ...
            elif not model or not issubclass(model, allowed_models):
                return await func(self, node=None, info=info)
            async with info.context.get_session() as session:
                async with session.begin():
                    stmt = select(model).where(model.id == id_)
                    node = (await session.execute(stmt)).scalar_one_or_none()

            return await func(self, node=node, info=info)

        async def wrapper_action_on_node_nullable(
            self, id: Optional[strawberry.ID], info: Info
        ):
            return await wrapper_action_on_node(self, id, info)

        # preserve return annotations of original function
        func_to_wrap = (
            wrapper_action_on_node_nullable if id_nullable else wrapper_action_on_node
        )

        ret_ann = func.__annotations__["return"]
        func_to_wrap.__annotations__["return"] = ret_ann
        # wrap it in a strawberry.field
        args_for_str = strawberry_args or {}

        return strawberry.field(func_to_wrap, **args_for_str)

    if _func is None:
        return decorator_action_on_node
    else:
        return decorator_action_on_node(_func)


@strawberry.type
class NodeEdge:
    node: Optional[Node] = _RelayNodeField()


async def maybe_get_by_node_id(
    id_: Optional[strawberry.ID | str], model: Type[T], session: AsyncSession
) -> Optional[T]:
    _id = parse_and_validate_id(id_, model=model)
    if _id is None:
        return None
    o = (
        await session.execute(select(model).where(model.id == _id))
    ).scalar_one_or_none()
    return o


async def convert_and_check_exists_node_id(
    id_: strawberry.ID, model: Type, session: AsyncSession
) -> Optional[int]:
    _id = parse_and_validate_id(id_, model=model)
    if _id is None:
        return None
    ex = (
        await session.execute(exists(model).where(model.id == _id).select())
    ).scalar_one()
    if ex:
        return _id
    else:
        return None
