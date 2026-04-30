import asyncio
import random
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Body, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from .game import GameManager
from .matchmaking import Matchmaker
from .auth import create_token, decode_token

app = FastAPI()
manager = GameManager()
matchmaker = Matchmaker(manager)

clients = {}
TICK_RATE = 1 / 30


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    print(f"{request.url.path} took {duration:.4f}s")

    return response


app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def lobby():
    return FileResponse("frontend/lobby.html")


@app.get("/game")
async def game():
    return FileResponse("frontend/index.html")


@app.post("/create-room")
async def create_room(data: dict = Body(...)):
    room_id = data.get("room") or str(random.randint(100000, 999999))
    password = data.get("password")

    manager.create_room(
        room_id,
        private=True,
        password=password
    )

    return {"room": room_id}


# 🔐 AUTH (guest login)
@app.post("/login")
async def login():
    name = random.choice(["Alpha", "Blaze", "Ghost", "Viper"]
                         ) + str(random.randint(100, 999))
    token = create_token(name)

    return JSONResponse({
        "token": token,
        "username": name
    })


# 🎯 MATCHMAKING API
@app.get("/matchmake")
async def matchmake():
    room_id = matchmaker.find_room()
    return {"room": room_id}


# 🔌 WebSocket
@app.websocket("/ws")
async def ws(
    ws: WebSocket,
    token: str = Query(...),
    room: str = Query(None),
    password: str = Query(None)
):
    await ws.accept()

    user = decode_token(token)
    username = user["username"]

    # 🎯 Room selection
    if room:
        game_room = manager.get_room(room)

        if not game_room:
            await ws.close(code=4000)
            return

        # 🔒 Check private access
        if game_room.private:
            if game_room.password != password:
                await ws.close(code=4001)
                return
    else:
        room = matchmaker.find_room()
        game_room = manager.get_room(room)

    player = game_room.add_player()
    player.name = username

    clients[ws] = (room, player.id)

    await ws.send_json({
        "type": "init",
        "playerId": player.id,
        "name": username,
        "room": room
    })

    try:
        while True:
            data = await ws.receive_json()
            game_room.handle_input(player.id, data)

    except WebSocketDisconnect:
        game_room.remove_player(player.id)
        del clients[ws]

# 🔁 Game loop


async def game_loop():
    while True:
        for ws, (room_id, _) in list(clients.items()):
            room = manager.get_room(room_id)
            room.update(TICK_RATE)

            try:
                await ws.send_json({
                    "type": "state",
                    **room.serialize()
                })
            except:
                pass

        await asyncio.sleep(TICK_RATE)


@app.on_event("startup")
async def start():
    asyncio.create_task(game_loop())
