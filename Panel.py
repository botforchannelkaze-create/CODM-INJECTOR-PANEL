from flask import Flask, request
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app)

keys = {}
tokens = {}

# ======================
# CREATE TOKEN
# ======================
@app.route("/token")
def token():

    ref = request.headers.get("Referer","")

    if ("work.ink" not in ref) and ("kaze-key-page.onrender.com" not in ref):
        return "denied"

    token = str(uuid.uuid4())

    tokens[token] = {
        "time": time.time()
    }

    return token

# ======================
# GET KEY
# ======================
@app.route("/getkey")
def getkey():

    token = request.args.get("token")

    if token not in tokens:
        return "Access denied please go to main link"

    # token one time use
    del tokens[token]

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
