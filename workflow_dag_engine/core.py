"""Bounded asynchronous execution of validated local-operation DAGs."""

import asyncio, json, math, os, tempfile, time
from pathlib import Path

OPERATIONS = {"constant", "sum", "multiply", "sleep", "fail"}


def validate(spec):
    if not isinstance(spec, dict):
        raise ValueError("Workflow must be an object")
    tasks = spec.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("A nonempty tasks array is required")
    mapping = {}
    for task in tasks:
        if (
            not isinstance(task, dict)
            or not isinstance(task.get("id"), str)
            or not task["id"]
        ):
            raise ValueError("Every task needs a string ID")
        if task["id"] in mapping:
            raise ValueError("Duplicate task ID")
        if task.get("operation") not in OPERATIONS:
            raise ValueError("Unsupported operation")
        dependencies = task.get("depends_on", [])
        if (
            not isinstance(dependencies, list)
            or any(not isinstance(d, str) for d in dependencies)
            or len(set(dependencies)) != len(dependencies)
        ):
            raise ValueError("Dependencies must be unique task IDs")
        retries = task.get("retries", 0)
        timeout = task.get("timeout", 10)
        if type(retries) is not int or not 0 <= retries <= 5:
            raise ValueError("Retries must be between zero and five")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (float, int))
            or not math.isfinite(timeout)
            or not 0 < timeout <= 60
        ):
            raise ValueError("Timeout must be positive and at most sixty seconds")
        if task["operation"] == "sleep":
            seconds = task.get("value", 0)
            if (
                isinstance(seconds, bool)
                or not isinstance(seconds, (float, int))
                or not math.isfinite(seconds)
                or not 0 <= seconds <= 60
            ):
                raise ValueError("Sleep must be between zero and sixty seconds")
        mapping[task["id"]] = task
    visiting = set()
    visited = set()

    def walk(key):
        if key not in mapping:
            raise ValueError("Unknown dependency: " + key)
        if key in visiting:
            raise ValueError("Workflow contains a cycle")
        if key in visited:
            return
        visiting.add(key)
        for dependency in mapping[key].get("depends_on", []):
            walk(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in mapping:
        walk(key)
    return mapping


async def operate(task, inputs):
    operation = task["operation"]
    if operation == "constant":
        return task.get("value")
    if operation == "sleep":
        await asyncio.sleep(task.get("value", 0))
        return task.get("result")
    if operation == "fail":
        raise ValueError("Requested task failure")
    values = inputs + task.get("values", [])
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in values
    ):
        raise ValueError("Numeric operations require finite numbers")
    result = sum(values) if operation == "sum" else math.prod(values)
    if not math.isfinite(result):
        raise ValueError("Numeric result is not finite")
    return result


async def execute(spec, workers=4):
    if type(workers) is not int or not 1 <= workers <= 32:
        raise ValueError("Workers must be between one and thirty-two")
    mapping = validate(spec)
    results = {}
    futures = {}
    semaphore = asyncio.Semaphore(workers)

    async def run(key):
        task = mapping[key]
        dependencies = task.get("depends_on", [])
        inputs = await asyncio.gather(*(futures[d] for d in dependencies))
        if any(result["status"] != "completed" for result in inputs):
            results[key] = {
                "status": "skipped",
                "attempts": 0,
                "reason": "Dependency failed",
            }
            return results[key]
        started = time.monotonic()
        async with semaphore:
            for attempt in range(task.get("retries", 0) + 1):
                try:
                    value = await asyncio.wait_for(
                        operate(task, [result["value"] for result in inputs]),
                        timeout=task.get("timeout", 10),
                    )
                    results[key] = {
                        "status": "completed",
                        "attempts": attempt + 1,
                        "value": value,
                    }
                    break
                except (ValueError, TypeError, OverflowError, TimeoutError) as exc:
                    results[key] = {
                        "status": "failed",
                        "attempts": attempt + 1,
                        "error": str(exc) or "Task timed out",
                    }
            results[key]["duration_ms"] = round((time.monotonic() - started) * 1000, 3)
        return results[key]

    # Futures are all registered before coroutines execute, regardless of input ordering.
    for key in mapping:
        futures[key] = asyncio.create_task(run(key))
    await asyncio.gather(*futures.values())
    return {
        "tasks": results,
        "success": all(row["status"] == "completed" for row in results.values()),
    }


def write_journal(path, result):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        temporary = Path(stream.name)
        json.dump(result, stream, indent=2, allow_nan=False)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
