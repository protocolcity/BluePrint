# Compatibility architecture

Current architecture is defined in [the root architecture](../ARCHITECTURE.md).
`overview/v1/serve.py` owns the application, `map/v1/` owns current spatial
modules, WorkLane owns records and WorkForce owns execution.

Files retained under `suite/` are compatibility assets/helpers. Before removing
one, inspect imports and packaged resource consumers and test those paths.
Do not introduce new business logic, a second state authority or a competing
HTTP app here. Old projection/animation designs are historical and do not
override current instructions or the product contract.
