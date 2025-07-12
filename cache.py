import datetime
from functools import wraps

cache_store = {}


def cache(seconds):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache = cache_store.get(func.__name__, None)
            print(f"Cache for {func.__name__}: {cache}")
            crr_time = datetime.datetime.now()

            if cache and cache["expiry"] > crr_time:
                return cache["result"]

            result = await func(*args, **kwargs)

            expiry = crr_time + datetime.timedelta(seconds=seconds)
            cache_store[func.__name__] = {"result": result, "expiry": expiry}
            return result

        return wrapper

    return decorator
