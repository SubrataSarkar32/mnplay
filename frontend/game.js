const config = {
    type: Phaser.AUTO,
    width: 800,
    height: 500,
    physics: { default: 'arcade' },
    scene: { preload, create, update },
    scale: {
        mode: Phaser.Scale.FIT,
        autoCenter: Phaser.Scale.CENTER_BOTH
    }
};

new Phaser.Game(config);

let socket, myId, myName;
let players = {}, texts = {};
let cursors, spaceKey;
let joystick = { x: 0, y: 0 };
const isMobile = /Mobi|Android/i.test(navigator.userAgent);

function setupJoystick() {
    const joy = document.getElementById("joystick");

    let active = false;

    joy.addEventListener("touchstart", () => active = true);

    joy.addEventListener("touchmove", (e) => {
        if (!active) return;

        const rect = joy.getBoundingClientRect();
        const touch = e.touches[0];

        joystick.x = (touch.clientX - rect.left - 50) / 50;
        joystick.y = (touch.clientY - rect.top - 50) / 50;
    });

    joy.addEventListener("touchend", () => {
        active = false;
        joystick = { x: 0, y: 0 };
    });
}

let shootPressed = false;

function setupShoot() {
    const btn = document.getElementById("shootBtn");

    btn.addEventListener("touchstart", () => shootPressed = true);
    btn.addEventListener("touchend", () => shootPressed = false);
}

function preload() {
    this.load.image("tiles", "tiles.png");
    this.load.tilemapTiledJSON("map", "map.json");
}

function createPlayerTexture(scene) {
    if (scene.textures.exists("player")) return;
    const g = scene.make.graphics({ x: 0, y: 0, add: false });
    g.fillStyle(0xffffff);
    g.fillRect(0, 0, 30, 30);
    g.generateTexture("player", 30, 30);
    g.destroy();
}

function create() {
    createPlayerTexture(this);
    cursors = this.input.keyboard.createCursorKeys();
    spaceKey = this.input.keyboard.addKey(
        Phaser.Input.Keyboard.KeyCodes.SPACE
    );

    const map = this.make.tilemap({ key: "map" });
    const tileset = map.addTilesetImage("tiles");
    const layer = map.createLayer(0, tileset, 0, 0);
    if (isMobile) {
        setupJoystick();
        setupShoot();
    }

    layer.setCollision([1]);

    const protocol = location.protocol === "https:" ? "wss" : "ws";

    socket = new WebSocket(
    `${protocol}://${location.host}/ws?token=${TOKEN}&room=${ROOM_ID}&password=${PASSWORD}`
    );

    socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "init") {
            myId = msg.playerId;
            myName = msg.name;
            return;
        }

        if (msg.type === "state") {
            updatePlayers.call(this, msg.players, layer);
        }
    };
}

function updatePlayers(playersData, layer) {
    playersData.forEach(p => {
        if (!players[p.id]) {
            players[p.id] = this.physics.add.sprite(p.x, p.y, "player")
                .setDisplaySize(30, 30)
                .setTint(p.id === myId ? 0x0000ff : 0x00ff00);

            texts[p.id] = this.add.text(p.x, p.y - 20, p.name, {
                fontSize: "12px",
                color: "#ffffff"
            });

            this.physics.add.collider(players[p.id], layer);
        }
        if (!players[p.id].healthBar) {
            players[p.id].healthBar = this.add.rectangle(p.x, p.y - 25, 30, 5, 0xff0000);
        }

        players[p.id].healthBar.width = 30 * (p.health / 100);
        players[p.id].healthBar.x = players[p.id].x;
        players[p.id].healthBar.y = players[p.id].y - 25;

        players[p.id].x += (p.x - players[p.id].x) * 0.3;
        players[p.id].y += (p.y - players[p.id].y) * 0.3;

        texts[p.id].x = players[p.id].x - 20;
        texts[p.id].y = players[p.id].y - 40;

        if (p.id === myId) {
            this.cameras.main.startFollow(players[p.id]);
        }
    });

    Object.keys(players).forEach(id => {
        if (!playersData.find(p => p.id === id)) {
            players[id].destroy();
            texts[id].destroy();
            delete players[id];
            delete texts[id];
        }
    });
}

function update() {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;

    const pointer = this.input.activePointer;
    const me = players[myId];

    let angle = 0;

    if (me) {
        angle = Phaser.Math.Angle.Between(
            me.x, me.y,
            pointer.worldX, pointer.worldY
        );
    }
    let input;

    if (isMobile) {
        input = {
            left: joystick.x < -0.3,
            right: joystick.x > 0.3,
            jump: joystick.y < -0.5,
            jetpack: joystick.y < -0.5,
            shoot: shootPressed,
            angle: angle
        };
    } else {
        input = {
            left: cursors.left.isDown,
            right: cursors.right.isDown,
            jump: cursors.up.isDown,
            jetpack: cursors.up.isDown,
            shoot: spaceKey.isDown,
            angle: angle
        };
    }

    socket.send(JSON.stringify(input));
}