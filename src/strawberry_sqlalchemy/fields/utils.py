from typing import List, Union, Iterable

from strawberry.types.nodes import SelectedField, InlineFragment, FragmentSpread


def drill_for_field_names(
        selections: List[Union[
            SelectedField, InlineFragment, FragmentSpread
        ]]
) -> Iterable[str]:
    # TODO: parse type conditions
    #  to load efficiently interfaced types, e.g. inheritances
    # TODO 2: add logic to handle @skip and @include directives
    for selection in selections:
        if isinstance(selection, SelectedField):
            yield selection.name
        elif isinstance(selection, InlineFragment):
            yield from drill_for_field_names(selection.selections)
        elif isinstance(selection, FragmentSpread):
            yield from drill_for_field_names(selection.selections)
        else:
            raise TypeError(f"Unknown node type: {selection}")
