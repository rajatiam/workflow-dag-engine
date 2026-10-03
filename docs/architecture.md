# Workflow DAG Engine: architecture

## Dependency futures and bounded work

Validation rejects cycles, unknown dependencies, duplicate IDs and unsupported operations. All futures are registered before execution so dependency order in the input is irrelevant. A semaphore bounds simultaneous operations; task-local timeouts and retries keep failure handling explicit.

## Module boundaries

`workflow_dag_engine/core.py` contains the algorithm and persistence operations. `cli.py` validates arguments and prints JSON. The package entrypoint translates input and storage errors into structured stderr with exit status 2. Domain-specific unsuccessful results can use exit status 1. There is no shared runtime dependency on the portfolio folder.

## Failure and operational boundaries

Failed dependencies cause downstream tasks to skip, while independent branches still complete. The journal is published atomically after the run. Retries can repeat side effects if the operation set is later extended. No arbitrary shell execution, distributed scheduling or crash resume is implemented.

## Verification

Core tests cover valid results and failure boundaries. Process-level CLI tests run the committed examples in temporary copies, inspect JSON output and verify domain outcomes. CI runs on Python 3.11 and 3.13, Linux and Windows, checks package installation, and builds and executes the non-root Docker image.

## Extension choices

The standard-library implementation keeps local execution inspectable and offline. A hosted or distributed version would require workload-specific authorization, resource limits, durable coordination and observability. Extend the core through tested functions rather than adding infrastructure without a scaling requirement.
