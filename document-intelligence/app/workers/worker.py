"""
Start ARQ worker:

  cd document-intelligence
  arq app.workers.worker.WorkerSettings

Or:

  python -m app.workers.worker
"""

from __future__ import annotations

from arq.connections import RedisSettings

from app.config import get_settings
from app.workers.tasks import process_document_task


def _redis() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    functions = [process_document_task]
    redis_settings = _redis()
    queue_name = get_settings().arq_queue_name
    max_jobs = 10
    job_timeout = 600


if __name__ == "__main__":
    import subprocess
    import sys

    sys.exit(subprocess.call(["arq", "app.workers.worker.WorkerSettings"]))
