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

TOKEN_EXPIRY = 60
KEY_EXPIRY = 1800
DATA_FILE = "database.json"

# ======================
# LOAD DATABASE
# ======================

if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        db = json.load(f)
else:
    db = {
        "keys": {},
        "tokens": {}
    }

def save_db():
    with open(DATA_FILE, "w") as f:
        json.dump(db, f, indent=4)

# ======================
# TIME FORMAT
# ======================

def format_time(seconds):
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    return f"{days}d {hours}h {minutes}m"

def format_datetime(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

# ======================
# HOME
# ======================

@app.route("/")
def home():
    return "KAZE PANEL ONLINE 🚀"

# ======================
# TOKEN
# ======================

@app.route("/token")
def token():

    token_id = str(uuid.uuid4())

    db["tokens"][token_id] = {
        "time": time.time()
    }

    save_db()

    return token_id

# ======================
# GENERATE KEY
# ======================

@app.route("/getkey")
def getkey():

    token_id = request.args.get("token")

    if not token_id or token_id not in db["tokens"]:
        return jsonify({"status":"error","message":"invalid token"}),403

    now = time.time()

    token_data = db["tokens"][token_id]

    if now - token_data["time"] > TOKEN_EXPIRY:
        del db["tokens"][token_id]
        save_db()
        return jsonify({"status":"error","message":"token expired"}),403

    # generate key
    key = "KazeFreeKey-" + ''.join(random.choices(string.ascii_letters + string.digits,k=12))

    db["keys"][key] = {
        "expiry": now + KEY_EXPIRY,
        "device": None,
        "revoked": False,
        "login_time": None
    }

    del db["tokens"][token_id]

    save_db()

    return jsonify({
        "status":"success",
        "key":key
    })

# ======================
# VERIFY
# ======================

@app.route("/verify")
def verify():

    key = request.args.get("key")
    device = request.args.get("device")

    if not key or key not in db["keys"]:
        return jsonify({"status":"invalid"})

    data = db["keys"][key]

    if data["revoked"]:
        return jsonify({"status":"revoked"})

    now = time.time()

    if now > data["expiry"]:
        return jsonify({"status":"expired"})

    if data["device"] is None:
        data["device"] = device
        data["login_time"] = now
        save_db()

    if data["device"] != device:
        return jsonify({"status":"locked"})

    remaining = int(data["expiry"] - now)

    return jsonify({
        "status":"valid",
        "key":key,
        "device":device,
        "expires_at":format_datetime(data["expiry"]),
        "remaining":format_time(remaining),
        "login_time":format_datetime(data["login_time"])
    })

# ======================
# REVOKE
# ======================

@app.route("/revoke")
def revoke():

    key = request.args.get("key")

    if key not in db["keys"]:
        return jsonify({"status":"error"}),404

    db["keys"][key]["revoked"] = True
    save_db()

    return jsonify({"status":"success"})

# ======================
# LIST
# ======================

@app.route("/list")
def list_keys():

    result = []

    now = time.time()

    for key,data in db["keys"].items():

        if data["revoked"]:
            continue

        if now > data["expiry"]:
            continue

        remaining = int(data["expiry"] - now)

        result.append({
            "key":key,
            "device":data["device"],
            "remaining":format_time(remaining)
        })

    return jsonify(result)

# ======================
# STATS
# ======================

@app.route("/stats")
def stats():

    total = len(db["keys"])

    now = time.time()

    active = len([
        k for k in db["keys"]
        if not db["keys"][k]["revoked"]
        and now < db["keys"][k]["expiry"]
    ])

    expired = total - active

    return jsonify({
        "total_keys":total,
        "active_keys":active,
        "expired_keys":expired
    })

# ======================
# RUN
# ======================

if __name__ == "__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
