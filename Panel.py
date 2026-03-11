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
COOLDOWN = 60
KEY_EXPIRY = 180


# ======================
# CLEANUP FUNCTION
# ======================
def cleanup():
    now = time.time()

    # remove expired tokens only
    expired_tokens = [t for t,d in tokens.items() if now - d["time"] > TOKEN_EXPIRY]
    for t in expired_tokens:
        del tokens[t]


# ======================
# CREATE TOKEN
# ======================
@app.route("/token")
def token():

    cleanup()

    ref = request.headers.get("Referer","")
    ip = request.remote_addr

    if ("work.ink" not in ref) and ("kaze-key-page.onrender.com" not in ref):
        return "Access denied"

    if ip in ip_cooldown and time.time() - ip_cooldown[ip] < COOLDOWN:
        return "Please wait before getting another key"

    t = str(uuid.uuid4())

    tokens[t] = {
        "time": time.time(),
        "ip": ip
    }

    return t


# ======================
# GET KEY
# ======================
@app.route("/getkey")
def getkey():

    cleanup()

    token = request.args.get("token")
    ip = request.remote_addr

    if not token or token not in tokens:
        return "Access denied please go to main link"

    data = tokens[token]

    if time.time() - data["time"] > TOKEN_EXPIRY:
        del tokens[token]
        return "Token expired"

    if data["ip"] != ip:
        del tokens[token]
        return "Access denied"

    del tokens[token]

    ip_cooldown[ip] = time.time()

    key = str(uuid.uuid4())

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

    # EXPIRED CHECK
    if time.time() > data["expiry"]:
        return "expired"

    # FIRST LOGIN
    if data["device"] is None:
        data["device"] = device
        return "valid"

    # SAME DEVICE
    if data["device"] == device:
        return "valid"

    # OTHER DEVICE
    return "locked"


# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
