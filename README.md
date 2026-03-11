# Limitations

## "Id" field
Each model must have a primary key field named "id", 
which is an integer. This is imposed as to generate
IDs for Nodes easily for any DB model.

## Model names
In short: model names must be unique, and alphanumeric.

Why? IDs. Keep reading further down if interested
in details.

How do I generate pretty IDs?
Pass model <-> int bijection to strawberry_sqlalchemy.

Two ways for that:
1. Set `__int_identity__` on the model classes you want.
2. Set `sqla_model_registry` in the relay.base before
any requests (everything that has to do with relay
types is lazy).
BTW `sqla_model_registry` is a bijective dict (`bidict`).


### Unique
Model names must be unique. This is imposed as to
generate unique Node ids for any DB model and instance.

You can think of it as of this: "ModelName:ID", which
at the core basically is what's happening.

Any clever way of generating unique IDs for models is 
doomed to fail, as IDs must be stable, and not change 
when the model is updated, or when a bunch of new models 
get added.

Thus, the only way to generate unique IDs is to use the
model table_name, and the model ID.

### Alphanumeric
Model names must be alphanumeric.
