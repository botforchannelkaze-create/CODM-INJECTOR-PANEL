from flask import Flask, request
from flask_cors import CORS
import uuid, time

app = Flask(__name__)
CORS(app)  # allow cross-site requests

keys = {}

@app.route("/getkey")
def getkey():
    key = str(uuid.uuid4())
    keys[key] = {"expiry": time.time()+86400, "device": None}
    return f"YOUR KEY: {key}"

@app.route("/verify")
def verify():
    key = request.args.get("key")
    device = request.args.get("device")

    if key not in keys:
        return "invalid"

    data = keys[key]

    if time.time() > data["expiry"]:
        return "expired"

    if data["device"] is None:
        data["device"] = device
        return "valid"

    if data["device"] == device:
        return "valid"

    return "locked"

import os
app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
