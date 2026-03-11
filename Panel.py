from flask import Flask, request
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app)

# storage
keys = {}
ip_cooldown = {}

# =========================
# GET KEY
# =========================
@app.route("/getkey")
def getkey():

    ref = request.headers.get("Referer","")
    ip = request.remote_addr
    now = time.time()

    # allow only work.ink or your key page
    if ("work.ink" not in ref) and ("kaze-key-page.onrender.com" not in ref):
        return "Access denied"

    # anti spam (30 sec cooldown per IP)
    if ip in ip_cooldown:
        if now - ip_cooldown[ip] < 30:
            wait = int(30 - (now - ip_cooldown[ip]))
            return f"Please wait {wait}s before generating another key"

    ip_cooldown[ip] = now

    # generate key
    key = str(uuid.uuid4())

    keys[key] = {
        "expiry": time.time() + 86400,  # 24 hours
        "device": None
    }

    return f"YOUR KEY: {key}"

# =========================
# VERIFY KEY
# =========================
@app.route("/verify")
def verify():

    key = request.args.get("key")
    device = request.args.get("device")

    if key not in keys:
        return "invalid"

    data = keys[key]

    # check expiration
    if time.time() > data["expiry"]:
        del keys[key]
        return "expired"

    # first device bind
    if data["device"] is None:
        data["device"] = device
        return "valid"

    # same device
    if data["device"] == device:
        return "valid"

    # different device
    return "locked"

# =========================
# RUN SERVER
# =========================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT",10000))
)
