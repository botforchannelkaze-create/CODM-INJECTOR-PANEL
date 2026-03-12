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
TOKEN_EXPIRY = 60       # seconds
KEY_EXPIRY = 60      # 24h
COOLDOWN = 10           # seconds between token requests
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
    ref = request.headers.get("Referer","")
    ip = request.remote_addr
    now = time.time()

    # Check referrer (optional, enable if using Work.ink)
    # if "work.ink" not in ref:
    #     return "Access denied please go to main link",403

    # 1 key per day limit
    if ip in db["ip_daily"] and now - db["ip_daily"][ip] < 60:
        return "Access denied please go to main link",403

    # cooldown
    if ip in db["cooldown"] and now - db["cooldown"][ip] < COOLDOWN:
        return f"Cooldown active. Wait {int(COOLDOWN - (now - db['cooldown'][ip]))}s",429

    token_id = str(uuid.uuid4())
    db["tokens"][token_id] = {
        "ip": ip,
        "time": now
    }
    db["cooldown"][ip] = now
    save_db()

    return token_id

# ======================
# Get Key
# ======================
@app.route("/getkey")
def getkey():
    token_id = request.args.get("token")
    ip = request.remote_addr
    now = time.time()

    if not token_id or token_id not in db["tokens"]:
        return jsonify({"status":"error","message":"Invalid token"}),403

    data = db["tokens"][token_id]
    if data["ip"] != ip:
        return jsonify({"status":"error","message":"IP mismatch"}),403

    if now - data["time"] > TOKEN_EXPIRY:
        return jsonify({"status":"error","message":"Token expired"}),403

    # Generate key
    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()
    db["keys"][key] = {
        "expiry": now + KEY_EXPIRY,
        "device": None
    }

    db["ip_daily"][ip] = now
    del db["tokens"][token_id]
    save_db()

    return jsonify({"status":"success","key": key})

# ======================
# Verify Key
# ======================
@app.route("/verify")
def verify():
    key = request.args.get("key")
    device = request.args.get("device")

    if not key or key not in db["keys"]:
        return "invalid"

    data = db["keys"][key]

    if time.time() > data["expiry"]:
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
