# Limitations

## "Id" field

Each model must have a primary key field named `id`, which is an integer. This
is imposed to generate IDs for Relay nodes for any DB model.

## Model names

In short: model names must be unique and alphanumeric.

Why? IDs. Keep reading further down if interested in details.

How do I generate pretty IDs?
Pass a model <-> int bijection to `strawberry_chemist`.

Two ways for that:

1. Set `__int_identity__` on the model classes you want.
2. Set `sqla_model_registry` in `relay.base` before any requests.

`sqla_model_registry` is a bijective dict (`bidict`).

### Unique

Model names must be unique. This is imposed to generate unique node IDs for
any DB model and instance.

You can think of it as `"ModelName:ID"`, which is basically what is happening
at the core.

Any clever way of generating unique IDs for models is doomed to fail, because
IDs must be stable and must not change when the model is updated or when a
bunch of new models get added.

Thus, the only stable way to generate unique IDs is to use the model name and
the model ID.

### Alphanumeric

Model names must be alphanumeric.
