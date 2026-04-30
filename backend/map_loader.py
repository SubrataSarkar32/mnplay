import json


class TileMap:
    def __init__(self, path):
        with open(path) as f:
            data = json.load(f)

        self.tile_size = data["tileSize"]
        self.tiles = data["tiles"]

    def is_solid(self, x, y):
        tx = int(x // self.tile_size)
        ty = int(y // self.tile_size)

        if ty < 0 or ty >= len(self.tiles):
            return False
        if tx < 0 or tx >= len(self.tiles[0]):
            return False

        return self.tiles[ty][tx] == 1
