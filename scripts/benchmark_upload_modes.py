from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter, sleep


DATASETS = {
    "small": {"jobs": 8, "parts_per_job": 4, "delay_seconds": 0.01},
    "large": {"jobs": 3, "parts_per_job": 8, "delay_seconds": 0.015},
    "mixed": {"jobs": 5, "parts_per_job": 6, "delay_seconds": 0.012},
}


def _run_part(delay_seconds: float) -> None:
    sleep(delay_seconds)


def _run_job(parts_per_job: int, delay_seconds: float, part_concurrency: int) -> None:
    with ThreadPoolExecutor(max_workers=part_concurrency) as pool:
        futures = [pool.submit(_run_part, delay_seconds) for _ in range(parts_per_job)]
        for future in as_completed(futures):
            future.result()


def _measure_dataset(
    job_count: int,
    parts_per_job: int,
    delay_seconds: float,
    job_concurrency: int,
    part_concurrency: int,
) -> dict:
    started_at = perf_counter()
    with ThreadPoolExecutor(max_workers=job_concurrency) as pool:
        futures = [
            pool.submit(_run_job, parts_per_job, delay_seconds, part_concurrency)
            for _ in range(job_count)
        ]
        for future in as_completed(futures):
            future.result()
    duration = perf_counter() - started_at
    total_parts = job_count * parts_per_job
    return {
        "duration_seconds": duration,
        "jobs": job_count,
        "parts": total_parts,
        "average_parts_per_second": 0.0
        if duration == 0
        else round(total_parts / duration, 2),
    }


def run_benchmark_suite() -> dict:
    serial: dict[str, dict] = {}
    concurrent: dict[str, dict] = {}
    for dataset_name, dataset in DATASETS.items():
        serial[dataset_name] = _measure_dataset(
            dataset["jobs"],
            dataset["parts_per_job"],
            dataset["delay_seconds"],
            job_concurrency=1,
            part_concurrency=1,
        )
        concurrent[dataset_name] = _measure_dataset(
            dataset["jobs"],
            dataset["parts_per_job"],
            dataset["delay_seconds"],
            job_concurrency=2,
            part_concurrency=3,
        )
    return {"serial": serial, "concurrent": concurrent}


def main() -> int:
    print(json.dumps(run_benchmark_suite(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
