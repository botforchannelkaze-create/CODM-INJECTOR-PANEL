from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app)

# Database sa memory (Mas mainam kung sa Redis o SQLite pero ito muna para sa Render)
keys = {}
tokens = {}
ip_cooldown = {}
used_tokens = set() # Dagdag ito para hindi ma-reuse ang token

TOKEN_EXPIRY = 60 # Gawin nating 1 minute para hindi sila masyadong madaliin
COOLDOWN = 300   # 5 minutes cooldown bago makakuha ulit ng panibagong key
KEY_EXPIRY = 86400 # 24 Hours para sa user convenience

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

@app.route("/token")
def create_token():
    cleanup()
    
    # Mas mahigpit na check
    ref = request.headers.get("Referer","")
    ip = request.remote_addr

    # Siguraduhin na galing lang sa Work.ink ang request
    if "work.ink" not in ref:
        return "ERROR: Please use the official link.", 403

    # Cooldown Check
    if ip in ip_cooldown and time.time() - ip_cooldown[ip] < COOLDOWN:
        return "COOLDOWN: Please wait 5 minutes.", 429

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

    # Check if token exists, not expired, and not yet used
    if not token_input or token_input not in tokens:
        return "ACCESS DENIED: Go back to the main link.", 403
    
    if token_input in used_tokens:
        return "BYPASS DETECTED: Token already used.", 403

    data = tokens[token_input]

    # Security Checks
    if time.time() - data["time"] > TOKEN_EXPIRY:
        return "TOKEN EXPIRED: Refresh the link.", 403
    if data["ip"] != ip:
        return "IP MISMATCH: Don't use VPN/Proxy.", 403

    # Mark as used and start cooldown
    used_tokens.add(token_input)
    ip_cooldown[ip] = time.time()
    del tokens[token_input]

    # Generate the actual key
    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()
    keys[key] = {
        "expiry": time.time() + KEY_EXPIRY,
        "device": None
    }

    # I-return natin bilang JSON para mas malinis sa website mo
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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
