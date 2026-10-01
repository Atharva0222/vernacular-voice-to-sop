from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory, per-process. Fine for a single instance; a multi-worker/horizontally scaled
# deployment would need a shared backend (e.g. Redis) for the limit to hold across processes.
limiter = Limiter(key_func=get_remote_address)
