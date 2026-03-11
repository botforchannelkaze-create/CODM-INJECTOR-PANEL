from flask import Flask, request
from flask_cors import CORS
import uuid, time, os

app = Flask(__name__)
CORS(app)

keys = {}

@app.route("/getkey")
def getkey():

    ref = request.headers.get("Referer","")

    # allow only if coming from work.ink
    if "work.ink" not in ref:
        return "Access denied"

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

app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
