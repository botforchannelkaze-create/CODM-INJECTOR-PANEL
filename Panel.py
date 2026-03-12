from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

keys = {}
tokens = {}

TOKEN_EXPIRY = 300 
KEY_EXPIRY = 86400 

def cleanup():
    now = time.time()
    for t in list(tokens.items()):
        if now - t[1]["time"] > TOKEN_EXPIRY:
            del tokens[t[0]]
    for k in list(keys.items()):
        if now > k[1]["expiry"]:
            del keys[k[0]]

@app.route("/")
def home():
    return "KAZE AUTO-ENFORCER IS LIVE! 🛡️"

@app.route("/token")
def create_token():
    cleanup()
    source = request.args.get("source")
    ip = request.remote_addr

    if source != "workink":
        return "BYPASS DETECTED: Go back to main link.", 403

    t = str(uuid.uuid4())
    tokens[t] = {"time": time.time(), "ip": ip}
    return t

@app.route("/getkey")
def getkey():
    cleanup()
    token_input = request.args.get("token")
    ip = request.remote_addr

    if not token_input or token_input not in tokens:
        return jsonify({"status": "error", "message": "Token Expired/Used. Get a new one from official link."}), 403
    
    # BURAHIN AGAD PARA HINDI MA-REFRESH
    del tokens[token_input] 

    key = "KazeKey-" + uuid.uuid4().hex[:12].upper()
    keys[key] = {"expiry": time.time() + KEY_EXPIRY, "device": None}

    return jsonify({"status": "success", "key": key})

@app.route("/verify")
def verify():
    key = request.args.get("key")
    device = request.args.get("device")
    if not key or key not in keys: return "invalid"
    if time.time() > keys[key]["expiry"]: return "expired"
    if keys[key]["device"] is None:
        keys[key]["device"] = device
        return "valid"
    return "valid" if keys[key]["device"] == device else "locked"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
