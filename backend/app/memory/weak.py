# Weak memory tier — in-memory TTL cache for guest users.
from cachetools import TTLCache
from app.config import GUEST_TTL_SECONDS, GUEST_CACHE_MAX_SIZE, GUEST_MAX_TURNS

_guest_cache = TTLCache(maxsize=GUEST_CACHE_MAX_SIZE, ttl=GUEST_TTL_SECONDS)


# Get recent chat messages for a guest user.
def get_context(guest_id):
    entry = _guest_cache.get(guest_id)
    if entry is None:
        return []
    return list(entry.get("messages", []))


# Add a message turn to the guest user session.
def add_turn(guest_id, role, content):
    entry = _guest_cache.get(guest_id, {"messages": []})
    entry["messages"].append({"role": role, "content": content})
    if len(entry["messages"]) > GUEST_MAX_TURNS:
        entry["messages"] = entry["messages"][-GUEST_MAX_TURNS:]
    _guest_cache[guest_id] = entry


# Clear a guest user's session from memory cache.
def clear(guest_id):
    _guest_cache.pop(guest_id, None)


# Return debug statistics for the guest memory cache.
def get_cache_stats():
    return {
        "current_size": len(_guest_cache),
        "max_size": _guest_cache.maxsize,
        "ttl": _guest_cache.ttl,
    }
