from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import json
import os
import random
import string
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ======================
# Constants
# ======================
TOKEN_EXPIRY = 60       # seconds for token expiry
KEY_EXPIRY = 1800       # 30 minutes for free key expiry
COOLDOWN = 10           # anti-spam cooldown
KEY_LIMIT = 60          # time before same IP can generate another key
DATA_FILE = "database.json"

# ======================
# Load DB
# ======================
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        db = json.load(f)
else:
    db = {
        "keys": {},
        "tokens": {},
        "ip_limit": {},
        "cooldowns": {}
    }

def save_db():
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=4)

# ======================
# Time Formatting
# ======================
def format_time(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    return f"{days}d {hours}h {minutes}m"

def format_datetime(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

# ======================
# CLEANUP
# ======================
def cleanup():
    now = time.time()
    # Remove expired tokens
    for t in list(db["tokens"].keys()):
        if now - db["tokens"][t]["time"] > TOKEN_EXPIRY:
            del db["tokens"][t]
    # Remove expired IP limits
    for ip in list(db["ip_limit"].keys()):
        if now - db["ip_limit"][ip] > KEY_LIMIT:
            del db["ip_limit"][ip]

# ======================
# HOME
# ======================
@app.route("/")
def home():
    return "KAZE SERVER ONLINE 🚀"

# ======================
# TOKEN
# ======================
@app.route("/token")
def token():
    cleanup()
    ip = request.remote_addr
    now = time.time()

    # anti spam cooldown
    if ip in db["cooldowns"] and now - db["cooldowns"][ip] < COOLDOWN:
        wait = int(COOLDOWN - (now - db["cooldowns"][ip]))
        return f"Cooldown active wait {wait}s", 429

    # BLOCK if already generated key
    if ip in db["ip_limit"]:
        wait = int(KEY_LIMIT - (now - db["ip_limit"][ip]))
        return f"Wait {wait}s before getting new key", 403

    token_id = str(uuid.uuid4())
    db["tokens"][token_id] = {"ip": ip, "time": now}
    db["cooldowns"][ip] = now
    save_db()
    return token_id

# ======================
# GENERATE KEY
# ======================
@app.route("/getkey")
def getkey():
    cleanup()
    token_id = request.args.get("token")
    ip = request.remote_addr
    now = time.time()

    if not token_id or token_id not in db["tokens"]:
        return jsonify({"status": "error", "message": "Please try again later"}), 403

    data = db["tokens"][token_id]
    if data["ip"] != ip:
        return jsonify({"status": "error", "message": "IP mismatch"}), 403
    if now - data["time"] > TOKEN_EXPIRY:
        del db["tokens"][token_id]
        save_db()
        return jsonify({"status": "error", "message": "Token expired"}), 403

    # Generate key
    key = "KazeFreeKey-" + ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    db["keys"][key] = {
        "expiry": now + KEY_EXPIRY,
        "device": None,
        "revoked": False,
        "login_time": None  # for future login detection
    }

    # lock IP for KEY_LIMIT seconds
    db["ip_limit"][ip] = now
    del db["tokens"][token_id]
    save_db()

    return jsonify({"status": "success", "key": key})

# ======================
# VERIFY KEY
# ======================
@app.route("/verify")
def verify():
    cleanup()
    key = request.args.get("key")
    device = request.args.get("device")
    now = time.time()

    if not key or key not in db["keys"]:
        return jsonify({"status": "invalid"})

    data = db["keys"][key]

    if data.get("revoked"):
        return jsonify({"status": "revoked"})

    if now > data["expiry"]:
        return jsonify({"status": "expired"})

    # First login assign device and login_time
    if data["device"] is None:
        data["device"] = device
        data["login_time"] = now
        save_db()

    if data["device"] != device:
        return jsonify({"status": "locked"})

    remaining = int(data["expiry"] - now)
    return jsonify({
        "status": "valid",
        "key": key,
        "device": data["device"],
        "expires_at": format_datetime(data["expiry"]),
        "remaining": format_time(remaining),
        "login_time": format_datetime(data.get("login_time", now))
    })

# ======================
# REVOKE KEY
# ======================
@app.route("/revoke")
def revoke():
    key = request.args.get("key")
    if not key or key not in db["keys"]:
        return jsonify({"status": "error", "message": "Key not found"}), 404

    db["keys"][key]["revoked"] = True
    save_db()
    return jsonify({"status": "success", "message": f"{key} revoked"})

# ======================
# LIST ACTIVE KEYS
# ======================
@app.route("/list")
def list_keys():
    cleanup()
    result = []

    for key, data in db["keys"].items():
        if data.get("revoked"):
            continue
        remaining = int(data["expiry"] - time.time())
        if remaining <= 0:
            continue
        result.append({
            "key": key,
            "device": data["device"],
            "expires_at": format_datetime(data["expiry"]),
            "remaining": format_time(remaining),
            "login_time": format_datetime(data.get("login_time", time.time()))
        })

    return jsonify(result)

# ======================
# STATS
# ======================
@app.route("/stats")
def stats():
    cleanup()
    total = len(db["keys"])
    active = len([k for k in db["keys"] if not db["keys"][k].get("revoked") and time.time() < db["keys"][k]["expiry"]])
    expired = total - active
    return jsonify({
        "total_keys": total,
        "active_keys": active,
        "expired_keys": expired
    })

# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
