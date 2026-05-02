import time
from .redis_client import r

LIMIT = 10   # actions
WINDOW = 1   # seconds


def is_allowed(player_id):
    key = f"rate:{player_id}"
    now = time.time()

    r.zadd(key, {str(now): now})
    r.zremrangebyscore(key, 0, now - WINDOW)

    count = r.zcard(key)

    return count < LIMIT
