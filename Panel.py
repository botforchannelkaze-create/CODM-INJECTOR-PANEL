from flask import Flask, request
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app)

keys = {}
tokens = {}
ip_cooldown = {}

TOKEN_EXPIRY = 20
KEY_EXPIRY = 180
COOLDOWN = 9000


# ======================
# CLEANUP FUNCTION
# ======================
def cleanup():

    now = time.time()

    # remove expired tokens
    expired_tokens = [t for t,d in tokens.items() if now - d["time"] > TOKEN_EXPIRY]
    for t in expired_tokens:
        del tokens[t]

    # remove expired keys
    expired_keys = [k for k,d in keys.items() if now > d["expiry"]]
    for k in expired_keys:
        del keys[k]


# ======================
# CREATE TOKEN
# ======================
@app.route("/token")
def token():

    cleanup()

    ref = request.headers.get("Referer","")
    ip = request.remote_addr

    # ALLOW ONLY GPLINKS OR KEY PAGE
    if ("gplinks.co" not in ref) and ("kaze-key-page.onrender.com" not in ref):
        return "Please go to main link: https://gplinks.co/Kaze-DailyGetFreeKey"

    # APPLY COOLDOWN ONLY IF NOT FROM GPLINKS
    if "gplinks.co" not in ref:
        if ip in ip_cooldown:
            remaining = COOLDOWN - (time.time() - ip_cooldown[ip])
            if remaining > 0:
                return f"Please wait {int(remaining)} seconds"

    token = str(uuid.uuid4())

    tokens[token] = {
        "time": time.time(),
        "ip": ip
    }

    return token


# ======================
# GET KEY
# ======================
@app.route("/getkey")
def getkey():

    cleanup()

    token = request.args.get("token")
    ip = request.remote_addr

    if not token:
        return "Access denied"

    if token not in tokens:
        return "Access denied please go to main link"

    data = tokens[token]

    # TOKEN EXPIRED
    if time.time() - data["time"] > TOKEN_EXPIRY:
        del tokens[token]
        return "Token expired"

    # IP MISMATCH
    if data["ip"] != ip:
        del tokens[token]
        return "Access denied"

    # ONE TIME TOKEN
    del tokens[token]

    # START COOLDOWN
    ip_cooldown[ip] = time.time()

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

    # KEY EXPIRED
    if time.time() > data["expiry"]:
        del keys[key]
        return "expired"

    # FIRST LOGIN BINDS DEVICE
    if data["device"] is None:
        data["device"] = device
        return "valid"

    # SAME DEVICE
    if data["device"] == device:
        return "valid"

    # OTHER DEVICE BLOCKED
    return "locked"


# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
