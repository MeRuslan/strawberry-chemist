from collections.abc import Iterable, Iterator, Sequence
from typing import TypeAlias

from strawberry.types.nodes import SelectedField, InlineFragment, FragmentSpread

SelectionNode: TypeAlias = SelectedField | InlineFragment | FragmentSpread


def drill_for_field_names(
    selections: Sequence[SelectionNode],
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


def iter_selected_fields(
    selections: Sequence[SelectionNode],
) -> Iterator[SelectedField]:
    for selection in selections:
        if isinstance(selection, SelectedField):
            yield selection


def find_selected_field(
    selections: Sequence[SelectionNode],
    name: str,
) -> SelectedField | None:
    for selection in iter_selected_fields(selections):
        if selection.name == name:
            return selection
    return None
