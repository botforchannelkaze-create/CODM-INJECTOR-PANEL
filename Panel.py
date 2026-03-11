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

TOKEN_EXPIRY = 30
COOLDOWN = 30

# ======================
# CREATE TOKEN
# ======================
@app.route("/token")
def token():

    ref = request.headers.get("Referer","")
    ip = request.remote_addr

    if ("work.ink" not in ref) and ("kaze-key-page.onrender.com" not in ref):
        return "denied"

    # IP cooldown
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

    token = request.args.get("token")
    ip = request.remote_addr

    if token not in tokens:
        return "Access denied please go to main link"

    data = tokens[token]

    # token expire
    if time.time() - data["time"] > TOKEN_EXPIRY:
        del tokens[token]
        return "Token expired"

    # ip mismatch protection
    if data["ip"] != ip:
        del tokens[token]
        return "Access denied"

    del tokens[token]

    ip_cooldown[ip] = time.time()

    key = str(uuid.uuid4())

    keys[key] = {
        "expiry": time.time() + 86400,
        "device": None
    }

    return f"YOUR KEY: {key}"


# ======================
# VERIFY
# ======================
@app.route("/verify")
def verify():

    key = request.args.get("key")
    device = request.args.get("device")

    if key not in keys:
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
