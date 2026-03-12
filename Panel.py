from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Thread
import uuid
import time
import os

# Isang App lang ang kailangan natin para sa lahat
app = Flask(__name__)
# Importante: payagan ang HTML mo na makapag-request dito
CORS(app, resources={r"/*": {"origins": "*"}})

# Databases sa memory
keys = {}
tokens = {}
ip_cooldown = {}
used_tokens = set()

TOKEN_EXPIRY = 60 
COOLDOWN = 300   
KEY_EXPIRY = 86400 

def cleanup():
    now = time.time()
    # Linisin ang expired tokens
    for t in list(tokens.keys()):
        if now - tokens[t]["time"] > TOKEN_EXPIRY:
            del tokens[t]
    # Linisin ang expired keys
    for k in list(keys.keys()):
        if now > keys[k]["expiry"]:
            del keys[k]

# Ito ang "Keep Alive" at Home Page mo
@app.route("/")
def home():
    return "KAZE SERVER IS ONLINE! 🚀"

@app.route("/token")
def create_token():
    cleanup()
    ref = request.headers.get("Referer", "")
    ip = request.remote_addr

    # Anti-Bypass: Check kung galing sa Work.ink
    if "work.ink" not in ref and "render.com" not in ref:
        return "ERROR: Please use the official link.", 403

    # Cooldown Check per IP
    if ip in ip_cooldown and time.time() - ip_cooldown[ip] < COOLDOWN:
        return f"COOLDOWN: Please wait {int(COOLDOWN - (time.time() - ip_cooldown[ip]))}s.", 429

    t = str(uuid.uuid4())
    tokens[t] = {
        "time": time.time(),
        "ip": ip
    }
    return t

@app.route("/getkey")
def getkey():
    cleanup()
    token_input = request.args.get("token")
    ip = request.remote_addr

    if not token_input or token_input not in tokens:
        return jsonify({"status": "error", "message": "Invalid or Expired Token"}), 403
    
    data = tokens[token_input]

    if data["ip"] != ip:
        return jsonify({"status": "error", "message": "IP Mismatch"}), 403

    # Mark as used and generate key
    ip_cooldown[ip] = time.time()
    del tokens[token_input] # Delete agad para 'di na ma-reuse

    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()
    keys[key] = {
        "expiry": time.time() + KEY_EXPIRY,
        "device": None
    }

    return jsonify({"status": "success", "key": key})

@app.route("/verify")
def verify():
    key = request.args.get("key")
    device = request.args.get("device")

    if not key or key not in keys:
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

if __name__ == "__main__":
    # Isang beses lang natin patatakbuhin ang app.run
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
