from functools import cached_property
from typing import List, Type

import strawberry
from strawberry import UNSET
from strawberry.annotation import StrawberryAnnotation
from strawberry.arguments import StrawberryArgument
from strawberry.field import StrawberryField
from strawberry.types.fields.resolver import StrawberryResolver, ReservedType

from strawberry_chemist.relay import maybe_get_by_node_id


class RelayResolver(StrawberryResolver):
    field: "RelayField"

    def link_field(self, field):
        self.field = field
        new_param = ReservedType(
            self.field.relay_kw["node_param_name"], self.field.relay_kw["model"]
        )
        self.RESERVED_PARAMSPEC = self.RESERVED_PARAMSPEC + (new_param,)
        pass

    # @cached_property
    # def annotations(self) -> Dict[str, object]:
    #     ann = super(RelayResolver, self).annotations
    #     ann[self.field.relay_kw['id_name']] = strawberry.ID
    #
    #     return ann

    async def __call__(self, *args, **kwargs):
        id = kwargs.pop(self.field.relay_kw["id_name"])
        info = kwargs["info"]
        async with info.context.get_session() as session:
            node = await maybe_get_by_node_id(
                id_=id, model=self.field.relay_kw["model"], session=session
            )
        self.field.origin = node

        kwargs[self.field.relay_kw["node_param_name"]] = node

        for permission_class in self.field.relay_kw["post_load_permission_classes"]:
            permission = permission_class()
            has_permission: bool

            has_permission = await permission.has_permission(node, **kwargs)
            if has_permission:
                continue
            message = getattr(permission, "message", None)
            raise PermissionError(message)

        return await super(RelayResolver, self).__call__(*args, **kwargs)

    @cached_property
    def arguments(self) -> List[StrawberryArgument]:
        args = super(RelayResolver, self).arguments
        argument = StrawberryArgument(
            python_name=self.field.relay_kw["id_name"],
            graphql_name=None,
            type_annotation=StrawberryAnnotation(
                annotation=strawberry.ID, namespace=self._namespace
            ),
        )
        args.append(argument)
        return args


class RelayField(StrawberryField):
    relay_kw: dict
    base_resolver: RelayResolver

    def set_relay_params(self, **kwargs):
        self.relay_kw = kwargs

    def __call__(self, resolver, *args, **kwargs):
        # Allow for StrawberryResolvers or bare functions to be provided
        if not isinstance(resolver, RelayResolver):
            resolver = RelayResolver(resolver)
            resolver.link_field(self)

        return super(RelayField, self).__call__(resolver=resolver)


def object_field(
    resolver=None,
    *,
    id_name: str = "id",
    node_param_name: str = "node",
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
    field_ = RelayField(
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
        node_param_name=node_param_name,
        model=model,
        post_load_permission_classes=node_permission_classes or [],
    )
    if resolver:
        return field_(resolver)
    return field_
