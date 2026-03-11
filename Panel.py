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
KEY_EXPIRY = 86400


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

    if ("work.ink" not in ref) and ("kaze-key-page.onrender.com" not in ref):
        return "Access denied"

    # anti spam cooldown
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

    if not token:
        return "Access denied"

    if token not in tokens:
        return "Access denied please go to main link"

    data = tokens[token]

    # token expiration
    if time.time() - data["time"] > TOKEN_EXPIRY:
        del tokens[token]
        return "Token expired"

    # IP verification
    if data["ip"] != ip:
        del tokens[token]
        return "Access denied"

    # one time token
    del tokens[token]

    # cooldown start
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

    if time.time() > data["expiry"]:
        del keys[key]
        return "expired"

    if data["device"] is None:
        data["device"] = device
        return "valid"

    if data["device"] == device:
        return "valid"

    return "locked"


# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
