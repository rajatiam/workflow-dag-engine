# Workflow DAG Engine

Concurrent dependency execution with retries, timeouts and failure propagation. An independent Python 3.11+ project using the standard library, with a real command-line interface and no runtime package dependencies.

## Run locally

From the cloned repository, run:

```sh
python -m workflow_dag_engine run examples/workflow.json --workers 3 --journal examples/run.json
python -m workflow_dag_engine validate examples/workflow.json
python -m workflow_dag_engine --help
```

Examples contain synthetic data. First use requires no cloud account, API key or package download. Optionally install the CLI using `python -m pip install .` and run `workflow-dag-engine --help`.

## Verify

```sh
python -m unittest discover -v
```

GitHub Actions checks Python 3.11 and 3.13 on Linux and Windows, verifies package installation, and builds/runs the non-root Docker image.

```sh
docker build -t workflow-dag-engine .
docker run --rm workflow-dag-engine --help
```

Mount a working directory at `/workspace` to process your own files. The container runs as UID 10001; provide appropriate write permissions for outputs.

## Architecture and scope

Business algorithms live in `workflow_dag_engine/core.py`; `workflow_dag_engine/cli.py` owns argument parsing and JSON output. Tests exercise success cases and failure boundaries, with temporary storage for mutations. See [design decisions](docs/architecture.md).

Only allowlisted local operations execute; no arbitrary commands or submitted Python are run. Work is at least once under retry, and the journal is a run result, not crash-resumable orchestration.

This project demonstrates implemented engineering practices. It does not claim production deployment history or external certifications.
