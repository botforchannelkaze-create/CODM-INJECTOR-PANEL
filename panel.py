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
TOKEN_EXPIRY = 60
KEY_EXPIRY = 180
COOLDOWN = 10
KEY_LIMIT = 60
DATA_FILE = "database.json"

# ======================
# Load DB
# ======================
if os.path.exists(DATA_FILE):
    with open(DATA_FILE,"r") as f:
        db = json.load(f)
else:
    db = {
        "keys":{},
        "tokens":{},
        "ip_limit":{},
        "cooldowns":{}
    }

def save_db():
    with open(DATA_FILE,"w") as f:
        json.dump(db,f)

# ======================
# CLEANUP
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

    # remove expired IP limits
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
        return f"Cooldown active wait {wait}s",429

    # BLOCK if already generated key
    if ip in db["ip_limit"]:
        wait = int(KEY_LIMIT - (now - db["ip_limit"][ip]))
        return f"Wait {wait}s before getting new key",403

    token_id = str(uuid.uuid4())

    db["tokens"][token_id] = {
        "ip": ip,
        "time": now
    }

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
        return jsonify({"status":"error","message":"Invalid token"}),403

    data = db["tokens"][token_id]

    if data["ip"] != ip:
        return jsonify({"status":"error","message":"IP mismatch"}),403

    if now - data["time"] > TOKEN_EXPIRY:
        del db["tokens"][token_id]
        save_db()
        return jsonify({"status":"error","message":"Token expired"}),403

    # generate key
    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()

    db["keys"][key] = {
        "expiry": now + KEY_EXPIRY,
        "device": None
    }

    # lock IP for KEY_LIMIT seconds
    db["ip_limit"][ip] = now

    del db["tokens"][token_id]

    save_db()

    return jsonify({
        "status":"success",
        "key": key
    })

# ======================
# VERIFY KEY
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
# RUN
# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
