import uuid

MAX_PLAYERS = 4


class Matchmaker:
    def __init__(self, manager):
        self.manager = manager

    def find_room(self):
        for room_id, room in self.manager.rooms.items():
            if room.private:
                continue

            if not room.is_full():
                return room_id

        new_room = str(uuid.uuid4())[:6]
        self.manager.create_room(new_room, private=False)
        return new_room
