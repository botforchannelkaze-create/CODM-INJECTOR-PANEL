from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import json
import os

app = Flask(__name__)
CORS(app)

# ======================
# Constants
# ======================
TOKEN_EXPIRY = 180       # token valid for 3 minutes
KEY_EXPIRY = 1800        # key valid for 30 minutes
COOLDOWN = 10            # seconds between token requests
KEY_LIMIT = 90           # 90 seconds before same IP can get new key
DATA_FILE = "database.json"

# ======================
# Load / Save DB
# ======================
if os.path.exists(DATA_FILE):
    with open(DATA_FILE,"r") as f:
        db = json.load(f)
else:
    db = {
        "keys":{},
        "tokens":{},
        "ip_daily":{},
        "cooldown":{}
    }

def save_db():
    with open(DATA_FILE,"w") as f:
        json.dump(db,f)

# ======================
# Cleanup expired data
# ======================
def cleanup():
    now = time.time()
    # remove expired tokens
    for t in list(db["tokens"].keys()):
        if now - db["tokens"][t]["time"] > TOKEN_EXPIRY:
            del db["tokens"][t]
    # remove expired keys
    for k in list(db["keys"].keys()):
        if now > db["keys"][k]["expiry"]:
            del db["keys"][k]

# ======================
# Home
# ======================
@app.route("/")
def home():
    return "KAZE SERVER ONLINE 🚀"

# ======================
# Get Token
# ======================
@app.route("/token")
def token():
    cleanup()
    ip = request.remote_addr
    now = time.time()

    # Limit per IP (90s)
    if ip in db["ip_daily"] and now - db["ip_daily"][ip] < KEY_LIMIT:
        return "Access denied please go to main link",403

    # Cooldown protection
    if ip in db["cooldown"] and now - db["cooldown"][ip] < COOLDOWN:
        wait = int(COOLDOWN - (now - db["cooldown"][ip]))
        return f"Cooldown active. Wait {wait}s",429

    token_id = str(uuid.uuid4())
    db["tokens"][token_id] = {"ip": ip, "time": now}
    db["cooldown"][ip] = now
    save_db()

    return token_id

# ======================
# Get Key
# ======================
@app.route("/getkey")
def getkey():
    cleanup()
    token_id = request.args.get("token")
    ip = request.remote_addr
    now = time.time()

    if not token_id or token_id not in db["tokens"]:
        return jsonify({"status":"error","message":"Invalid token"}),403

    data = db["tokens"][token_id]

    if data["ip"] != ip:
        return jsonify({"status":"error","message":"IP mismatch"}),403

    if now - data["time"] > TOKEN_EXPIRY:
        del db["tokens"][token_id]
        save_db()
        return jsonify({"status":"error","message":"Token expired"}),403

    # Generate key
    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()
    db["keys"][key] = {"expiry": now + KEY_EXPIRY, "device": None}
    db["ip_daily"][ip] = now

    del db["tokens"][token_id]
    save_db()

    return jsonify({"status":"success","key": key})

# ======================
# Verify Key
# ======================
@app.route("/verify")
def verify():
    cleanup()
    key = request.args.get("key")
    device = request.args.get("device")

    if not key or key not in db["keys"]:
        return "invalid"

    data = db["keys"][key]

    if time.time() > data["expiry"]:
        del db["keys"][key]
        save_db()
        return "expired"

    if data["device"] is None:
        data["device"] = device
        save_db()
        return "valid"

    if data["device"] == device:
        return "valid"

    return "locked"

# ======================
# Run
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
