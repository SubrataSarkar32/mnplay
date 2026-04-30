import redis
import json

r = redis.Redis(host="localhost", port=6379, decode_responses=True)


# ---- Rooms ----
def save_room(room_id, data):
    r.set(f"room:{room_id}", json.dumps(data))


def get_room(room_id):
    data = r.get(f"room:{room_id}")
    return json.loads(data) if data else None


def list_rooms():
    keys = r.keys("room:*")
    return [k.split(":")[1] for k in keys]
