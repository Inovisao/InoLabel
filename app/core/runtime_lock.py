"""Serialize access to the annotation runtime shared by API worker threads."""

from functools import wraps
from threading import RLock

runtime_lock = RLock()


def protect_state(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        with runtime_lock:
            return function(*args, **kwargs)
    return guarded
