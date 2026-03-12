from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app)

keys = {}
tokens = {}
# Ito ang magbabantay sa IP address nila
ip_usage = {} 

KEY_EXPIRY = 86400  # 24 hours validity ng key
COOLDOWN = 300      # 5 minutes bago makakuha ulit ng panibagong key ang IP

@app.route("/token")
def create_token():
    source = request.args.get("source")
    ip = request.remote_addr
    now = time.time()

    # 1. Anti-Bypass: Dapat dumaan sa link
    if source != "workink":
        return "DENIED: Use the official link.", 403

    # 2. 5-Minute Limit: Check kung nakakuha na ang IP na to recently
    if ip in ip_usage:
        if now - ip_usage[ip] < COOLDOWN:
            return "LIMIT: You can only get 1 key every 5 minutes.", 429

    t = str(uuid.uuid4())
    tokens[t] = {"ip": ip, "time": now}
    return t

@app.route("/getkey")
def getkey():
    token_input = request.args.get("token")
    ip = request.remote_addr

    if not token_input or token_input not in tokens:
        return jsonify({"status": "error", "message": "Expired/Invalid Token."}), 403
    
    if tokens[token_input]["ip"] != ip:
        return jsonify({"status": "error", "message": "IP Mismatch."}), 403

    # SUNUGIN AGAD ANG TOKEN AT I-RECORD ANG IP
    del tokens[token_input]
    ip_usage[ip] = time.time()

    key = "KazeKey-" + uuid.uuid4().hex[:12].upper()
    keys[key] = {"expiry": time.time() + KEY_EXPIRY, "device": None}

    return jsonify({"status": "success", "key": key})

@app.route("/verify")
def verify():
    key = request.args.get("key")
    device = request.args.get("device")
    if key in keys:
        if keys[key]["device"] is None or keys[key]["device"] == device:
            keys[key]["device"] = device
            return "valid"
    return "invalid"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
