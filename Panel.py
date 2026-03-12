from flask import Flask, request
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app)

keys = {}
sessions = {}
ip_limit = {}

TOKEN_EXPIRY = 20
KEY_EXPIRY = 180
KEY_INTERVAL = 43200   # 12 hours


# ======================
# CLEANUP
# ======================
def cleanup():

    now = time.time()

    expired_sessions = [s for s,d in sessions.items() if now - d["time"] > TOKEN_EXPIRY]
    for s in expired_sessions:
        del sessions[s]

    expired_keys = [k for k,d in keys.items() if now > d["expiry"]]
    for k in expired_keys:
        del keys[k]


# ======================
# CREATE SESSION TOKEN
# ======================
@app.route("/session")
def session():

    cleanup()

    ref = request.headers.get("Referer","")
    ip = request.remote_addr

    # allow only gplinks
    if "gplinks.co" not in ref:
        return "Access denied. Use main link: https://gplinks.co/Kaze-DailyGetFreeKey"

    # 12 hour limit
    if ip in ip_limit:
        remaining = KEY_INTERVAL - (time.time() - ip_limit[ip])
        if remaining > 0:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            return f"You already generated a key. Try again in {hours}h {minutes}m"

    token = str(uuid.uuid4())

    sessions[token] = {
        "ip": ip,
        "time": time.time(),
        "used": False
    }

    return token


# ======================
# GENERATE KEY
# ======================
@app.route("/getkey")
def getkey():

    cleanup()

    token = request.args.get("token")
    ip = request.remote_addr

    if not token:
        return "Access denied"

    if token not in sessions:
        return "Invalid session"

    data = sessions[token]

    # token already used
    if data["used"]:
        return "Session already used"

    # ip mismatch
    if data["ip"] != ip:
        return "Access denied"

    # token expired
    if time.time() - data["time"] > TOKEN_EXPIRY:
        del sessions[token]
        return "Session expired"

    sessions[token]["used"] = True

    # register ip usage
    ip_limit[ip] = time.time()

    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()

    keys[key] = {
        "expiry": time.time() + KEY_EXPIRY,
        "device": None
    }

    return f"YOUR KEY: {key}"


# ======================
# VERIFY KEY
# ======================
@app.route("/verify")
def verify():

    cleanup()

    key = request.args.get("key")
    device = request.args.get("device")

    if not key or key not in keys:
        return "invalid"

    data = keys[key]

    # key expired
    if time.time() > data["expiry"]:
        del keys[key]
        return "expired"

    # bind device
    if data["device"] is None:
        data["device"] = device
        return "valid"

    # same device
    if data["device"] == device:
        return "valid"

    return "locked"


# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
