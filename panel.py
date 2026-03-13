from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid, time, json, os, random, string
import threading

app = Flask(__name__)
CORS(app)

# ====== CONSTANTS ======
TOKEN_EXPIRY = 60       # seconds
KEY_EXPIRY_FREE = 1800 # 12 hours
KEY_EXPIRY_VIP = {
    "1d": 86400, "3d": 259200, "7d": 604800, "30d": 2592000, "lifetime": None
}
COOLDOWN = 10
KEY_LIMIT = 1200
DATA_FILE = "database.json"

# ====== LOAD DB ======
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        db = json.load(f)
else:
    db = {"keys": {}, "tokens": {}, "ip_limit": {}, "cooldowns": {}}

def save_db():
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=2)

# ====== CLEANUP ======
def cleanup():
    now = time.time()
    for t in list(db["tokens"].keys()):
        if now - db["tokens"][t]["time"] > TOKEN_EXPIRY:
            del db["tokens"][t]

# ====== TOKEN ======
@app.route("/token")
def token():
    cleanup()
    ip = request.remote_addr
    now = time.time()
    if ip in db["cooldowns"] and now - db["cooldowns"][ip] < COOLDOWN:
        wait = int(COOLDOWN - (now - db["cooldowns"][ip]))
        return f"Cooldown {wait}s", 429
    if ip in db["ip_limit"] and now - db["ip_limit"][ip] < KEY_LIMIT:
        wait = int(KEY_LIMIT - (now - db["ip_limit"][ip]))
        return f"Wait {wait}s", 403
    token_id = str(uuid.uuid4())
    db["tokens"][token_id] = {"ip": ip, "time": now}
    db["cooldowns"][ip] = now
    save_db()
    return token_id

# ====== GET KEY (FOR FREE/DEFAULT) ======
@app.route("/getkey")
def getkey():
    cleanup()
    token_id = request.args.get("token")
    ip = request.remote_addr
    now = time.time()

    if not token_id or token_id not in db["tokens"]:
        return jsonify({"status":"error","message":"Please try again later"}), 403

    data = db["tokens"][token_id]
    if data["ip"] != ip or now - data["time"] > TOKEN_EXPIRY:
        del db["tokens"][token_id]
        save_db()
        return jsonify({"status":"error","message":"Token expired or IP mismatch"}), 403

    # Generate free key
    key = "KazeFreeKey-" + ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    db["keys"][key] = {"expiry": now + KEY_EXPIRY_FREE, "device": None, "type": "FREE"}

    db["ip_limit"][ip] = now
    del db["tokens"][token_id]
    save_db()
    return jsonify({"status":"success","key":key})

# ====== VIP KEY GENERATOR (FOR BOT) ======
def generate_vip_key(duration):
    key = "Kaze-" + ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    expiry = None
    if duration in KEY_EXPIRY_VIP and KEY_EXPIRY_VIP[duration]:
        expiry = time.time() + KEY_EXPIRY_VIP[duration]
    db["keys"][key] = {"expiry": expiry, "device": None, "type": "VIP"}
    save_db()
    return key

# ====== VERIFY ======
@app.route("/verify")
def verify():
    cleanup()
    key = request.args.get("key")
    device = request.args.get("device")

    if not key or key not in db["keys"]:
        return "invalid"

    data = db["keys"][key]

    if data.get("expiry") and time.time() > data["expiry"]:
        data["expired"] = True
        save_db()
        return "expired"

    if data.get("device") is None:
        data["device"] = device
        save_db()
        return "valid"

    if data.get("device") == device:
        return "valid"

    return "locked"

@app.route("/vipgen")
def vipgen():
    duration = request.args.get("duration")
    if duration not in KEY_EXPIRY_VIP:
        return "invalid duration", 400
    key = generate_vip_key(duration)
    return key

# ====== RUN SERVER ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
