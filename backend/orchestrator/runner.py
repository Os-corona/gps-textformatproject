"""In-process job runners. Only committed job IDs cross the thread boundary."""
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock

from django.conf import settings
from django.db import close_old_connections, transaction

from .ai_pipeline import mark_job_error, run_ai_structuring

_executor = None
_executor_lock = Lock()


def _get_executor():
    global _executor
    with _executor_lock:
        if _executor is None:
            workers = getattr(settings, "JOB_RUNNER_MAX_WORKERS", 2)
            _executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="document-job")
        return _executor


def shutdown_runner(*, wait=True):
    """Release workers at application/test shutdown; a future enqueue creates a new pool."""
    global _executor
    with _executor_lock:
        executor, _executor = _executor, None
    if executor is not None:
        executor.shutdown(wait=wait)


def _thread_run(job_id):
    close_old_connections()
    try:
        return run_ai_structuring(job_id)
    except Exception as exc:
        mark_job_error(job_id, exc)
        raise
    finally:
        close_old_connections()


def enqueue(job_id) -> Future:
    """Schedule after transaction commit. sync executes inline; thread returns immediately."""
    backend = getattr(settings, "JOB_RUNNER", "thread")
    if backend not in ("sync", "thread"):
        raise ValueError("JOB_RUNNER debe ser 'sync' o 'thread'.")
    result = Future()

    def dispatch():
        if backend == "sync":
            try:
                result.set_result(run_ai_structuring(job_id))
            except Exception as exc:
                mark_job_error(job_id, exc)
                result.set_exception(exc)
            return
        try:
            task = _get_executor().submit(_thread_run, job_id)
        except Exception as exc:
            mark_job_error(job_id, exc)
            result.set_exception(exc)
            return

        def complete(future):
            try:
                value = future.result()
            except Exception as exc:
                if not result.done():
                    result.set_exception(exc)
            else:
                if not result.done():
                    result.set_result(value)

        task.add_done_callback(complete)

    transaction.on_commit(dispatch)
    return result
