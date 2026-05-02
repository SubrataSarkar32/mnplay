import uuid
import random
import math
from .map_loader import TileMap
from .logging_config import logger
from .rate_limiter import is_allowed
from .redis_client import save_room, get_room, list_rooms

tilemap = TileMap("shared/map.json")

GRAVITY = 500
PLAYER_SPEED = 200
JUMP_FORCE = -300
BULLET_SPEED = 500
RESPAWN_TIME = 3
PLAYER_SIZE = 30


class Bullet:
    def __init__(self, x, y, angle, owner):
        self.id = str(uuid.uuid4())
        self.x = x
        self.y = y
        self.vx = math.cos(angle) * BULLET_SPEED
        self.vy = math.sin(angle) * BULLET_SPEED
        self.owner = owner

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def to_dict(self):
        return {"id": self.id, "x": self.x, "y": self.y}


class Player:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.name = "Player"
        logger.info(f"Player joined: {self.id}")
        self.spawn()

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "health": self.health,
            "alive": self.alive
        }

    def spawn(self):
        self.x = random.randint(100, 500)
        self.y = 100
        self.vx = 0
        self.vy = 0
        self.health = 100
        self.alive = True
        self.respawn_timer = 0
        self.jetpack = 100
        self.on_ground = False


def move_with_collision(p, dt):
    # Horizontal
    new_x = p.x + p.vx * dt
    if not tilemap.is_solid(new_x, p.y):
        p.x = new_x

    # Vertical
    new_y = p.y + p.vy * dt

    if p.vy >= 0 and tilemap.is_solid(p.x, new_y + PLAYER_SIZE / 2):
        p.vy = 0
        p.on_ground = True
    elif p.vy < 0 and tilemap.is_solid(p.x, new_y - PLAYER_SIZE / 2):
        p.vy = 0
        p.on_ground = False
    else:
        p.y = new_y
        p.on_ground = False


class Room:
    def __init__(self, room_id, private=False, password=None):
        self.room_id = room_id
        self.players = {}
        self.bullets = []
        self.max_players = 4

        self.private = private
        self.password = password

    def is_full(self):
        return len(self.players) >= self.max_players

    def add_player(self):
        p = Player()
        self.players[p.id] = p
        return p

    def remove_player(self, pid):
        if pid in self.players:
            del self.players[pid]

    def handle_input(self, pid, data, dt=1/30):
        if not is_allowed(pid):
            return  # drop spam input

        p = self.players.get(pid)
        if not p or not p.alive:
            return

        p.vx = 0

        if data.get("left"):
            p.vx = -PLAYER_SPEED
        if data.get("right"):
            p.vx = PLAYER_SPEED

        if data.get("jump") and p.on_ground:
            p.vy = JUMP_FORCE

        if data.get("jetpack") and p.jetpack > 0:
            p.vy -= 400 * dt
            p.jetpack -= 20 * dt

        if data.get("shoot"):
            angle = data.get("angle", 0)
            self.bullets.append(Bullet(p.x, p.y, angle, p.id))

    def update(self, dt):
        for p in self.players.values():
            if not p.alive:
                p.respawn_timer -= dt
                if p.respawn_timer <= 0:
                    p.spawn()
                continue

            p.vy += GRAVITY * dt
            move_with_collision(p, dt)

        for b in self.bullets:
            b.update(dt)

        # Bullet collision
        for b in self.bullets:
            for p in self.players.values():
                if p.id == b.owner or not p.alive:
                    continue

                if abs(p.x - b.x) < 20 and abs(p.y - b.y) < 20:
                    p.health -= 20
                    if p.health <= 0:
                        p.alive = False
                        p.respawn_timer = RESPAWN_TIME

        self.bullets = [b for b in self.bullets if 0 < b.x < 2000]

    def serialize(self):
        return {
            "players": [p.to_dict() for p in self.players.values()],
            "bullets": [b.to_dict() for b in self.bullets]
        }


class GameManager:
    def __init__(self):
        self.rooms = {}

    def create_room(self, room_id, private=False, password=None):
        room = Room(room_id, private, password)
        self.rooms[room_id] = room
        return room

    def get_room(self, room_id):
        return self.rooms.get(room_id)

    def sync_room(self, room):
        save_room(room.room_id, {
            "players": len(room.players),
            "private": room.private
        })
