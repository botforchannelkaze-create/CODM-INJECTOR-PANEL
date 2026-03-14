from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import json
import os
import random
import string
import requests

app = Flask(__name__)
CORS(app)

DATA_FILE = "database.json"

TELEGRAM_BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")

# ======================
# LOAD DB
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
# TELEGRAM ALERT
# ======================

def send_telegram_alert(message: str):
    if not TELEGRAM_BOT_TOKEN or not OWNER_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={
                "chat_id": OWNER_ID,
                "text": message,
                "parse_mode": "Markdown"
            },
            timeout=5
        )
    except:
        pass

# ======================
# DURATION
# ======================

def convert_duration(duration: str):
    duration = duration.lower()

    if duration.endswith("m"):
        return int(duration[:-1]) * 60

    if duration.endswith("h"):
        return int(duration[:-1]) * 3600

    if duration.endswith("d"):
        return int(duration[:-1]) * 86400

    if duration == "lifetime":
        return 999999999

    return 43200  # default 12h

# ======================
# HOME
# ======================

@app.route("/")
def home():
    return "KAZE SERVER ONLINE 🚀"

# ======================
# TOKEN (NO LIMIT)
# ======================

@app.route("/token")
def token():
    token_id = str(uuid.uuid4())

    db["tokens"][token_id] = {
        "ip": request.remote_addr,
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
    source = request.args.get("src", "site")
    duration = request.args.get("duration", "12h")

    if not token_id or token_id not in db["tokens"]:
        return jsonify({
            "status": "error",
            "message": "invalid request"
        })

    now = time.time()

    if source == "bot":
        prefix = "Kaze-"
    else:
        prefix = "KazeFreeKey-"

    key = prefix + ''.join(random.choices(string.ascii_letters + string.digits, k=12))

    expiry_seconds = convert_duration(duration)

    db["keys"][key] = {
        "expiry": now + expiry_seconds,
        "device": None,
        "revoked": False,
        "login_time": None
    }

    del db["tokens"][token_id]

    save_db()

    return jsonify({
        "status": "success",
        "key": key,
        "expires_in": expiry_seconds
    })

# ======================
# VERIFY
# ======================

@app.route("/verify")
def verify():

    key = request.args.get("key")
    device = request.args.get("device")

    if not key or key not in db["keys"]:
        return "invalid"

    data = db["keys"][key]

    if data.get("revoked"):
        return "revoked"

    if time.time() > data["expiry"]:
        return "expired"

    if data["device"] is None:
        data["device"] = device
        data["login_time"] = time.time()
        save_db()
        return "valid"

    if data["device"] == device:
        return "valid"

    return "locked"

# ======================
# RUN
# ======================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
