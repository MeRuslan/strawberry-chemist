from functools import cached_property
from typing import List, Type

import strawberry
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument
from strawberry.types.fields.resolver import ReservedType

from strawberry_sqlalchemy.relay import convert_and_check_exists_node_id
from strawberry_sqlalchemy.relay.object_field import RelayResolver, RelayField


class RelayExistsResolver(RelayResolver):
    field: "RelayExistsField"

    def link_field(self, field):
        self.field = field
        new_param = ReservedType(self.field.relay_kw['exists_result'], self.field.relay_kw['model'])
        self.RESERVED_PARAMSPEC = (
            self.RESERVED_PARAMSPEC + (new_param, )
        )

    async def __call__(self, *args, **kwargs):
        id = kwargs.pop(self.field.relay_kw['id_name'])
        info = kwargs['info']
        async with info.context.get_session() as session:
            exists = await convert_and_check_exists_node_id(
                id_=id, model=self.field.relay_kw['model'], session=session
            )
        kwargs[self.field.relay_kw['exists_result']] = exists

        return await super(RelayResolver, self).__call__(*args, **kwargs)

    @cached_property
    def arguments(self) -> List[StrawberryArgument]:
        args = super(RelayResolver, self).arguments
        argument = StrawberryArgument(
            python_name=self.field.relay_kw['id_name'],
            graphql_name=None,
            type_annotation=StrawberryAnnotation(
                annotation=strawberry.ID, namespace=self._namespace
            )
        )
        args.append(argument)
        return args


class RelayExistsField(RelayField):
    base_resolver: RelayExistsResolver

    def __call__(self, resolver, *args, **kwargs):
        # Allow for StrawberryResolvers or bare functions to be provided
        if not isinstance(resolver, RelayExistsResolver):
            resolver = RelayExistsResolver(resolver)
            resolver.link_field(self)

        return super(RelayExistsField, self).__call__(resolver=resolver)


def object_exists_field(
    resolver=None,
    *,
    id_name: str = 'id',
    filtered_param_name: str = 'id',
    model: Type,
    name=None,
    is_subscription=False,
    description=None,
    permission_classes=None,
    node_permission_classes=None,
    deprecation_reason=None,
    default=UNSET,
    default_factory=UNSET,
    directives=(),
):
    field_ = RelayExistsField(
        python_name=None,
        graphql_name=None,
        type_annotation=None,
        description=description,
        is_subscription=is_subscription,
        permission_classes=permission_classes or [],
        deprecation_reason=deprecation_reason,
        default=default,
        default_factory=default_factory,
        directives=directives,
    )
    field_.set_relay_params(
        id_name=id_name,
        exists_result=filtered_param_name,
        model=model,
        post_load_permission_classes=node_permission_classes or [],
    )
    if resolver:
        return field_(resolver)
    return field_
