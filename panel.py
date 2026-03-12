from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import json
import os

app = Flask(__name__)
CORS(app)

TOKEN_EXPIRY = 60
KEY_EXPIRY = 86400
COOLDOWN = 100

DATA_FILE = "database.json"

# ======================
# LOAD DATABASE
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

def save():
    with open(DATA_FILE,"w") as f:
        json.dump(db,f)

# ======================
@app.route("/")
def home():
    return "KAZE SERVER ONLINE"

# ======================
@app.route("/token")
def token():
    ref = request.headers.get("Referer","")
    ip = request.remote_addr
    now = time.time()

    if "work.ink" not in ref:
        return "Access denied please go to main link",403

    if ip in db["ip_daily"]:
        if now - db["ip_daily"][ip] < 86400:
            return "Access denied please go to main link",403

    if ip in db["cooldown"]:
        if now - db["cooldown"][ip] < COOLDOWN:
            return "Cooldown active",429

    t = str(uuid.uuid4())

    db["tokens"][t] = {
        "ip":ip,
        "time":now
    }

    save()
    return t

# ======================
@app.route("/getkey")
def getkey():

    token = request.args.get("token")
    ip = request.remote_addr
    now = time.time()

    if token not in db["tokens"]:
        return jsonify({"status":"error","message":"Invalid token"}),403

    data = db["tokens"][token]

    if data["ip"] != ip:
        return jsonify({"status":"error","message":"IP mismatch"}),403

    if now - data["time"] > TOKEN_EXPIRY:
        return jsonify({"status":"error","message":"Token expired"}),403

    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()

    db["keys"][key] = {
        "expiry":now + KEY_EXPIRY,
        "device":None
    }

    db["ip_daily"][ip] = now
    db["cooldown"][ip] = now

    del db["tokens"][token]

    save()

    return jsonify({
        "status":"success",
        "key":key
    })

# ======================
@app.route("/verify")
def verify():

    key = request.args.get("key")
    device = request.args.get("device")

    if key not in db["keys"]:
        return "invalid"

    data = db["keys"][key]

    if time.time() > data["expiry"]:
        return "expired"

    if data["device"] is None:
        data["device"] = device
        save()
        return "valid"

    if data["device"] == device:
        return "valid"

    return "locked"

# ======================
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
