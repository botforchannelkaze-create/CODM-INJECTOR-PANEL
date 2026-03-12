from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
# Pinaka-importante para sa communication ng HTML at Flask
CORS(app, resources={r"/*": {"origins": "*"}})

# Databases sa memory
keys = {}
tokens = {}
already_generated = {} # IP-based tracking para sa Anti-Unli

TOKEN_EXPIRY = 300 
KEY_EXPIRY = 60 
REGENERATE_COOLDOWN = 6000 # 10 Minutes cooldown bago makakuha ulit ng key

def cleanup():
    now = time.time()
    # Linisin ang expired tokens
    for t in list(tokens.items()):
        if now - t[1]["time"] > TOKEN_EXPIRY:
            del tokens[t[0]]
    # Linisin ang expired keys
    for k in list(keys.items()):
        if now > k[1]["expiry"]:
            del keys[k[0]]

@app.route("/")
def home():
    return "KAZE ENFORCER IS LIVE! 🛡️"

@app.route("/token")
def create_token():
    cleanup()
    source = request.args.get("source")
    ip = request.remote_addr

    # 1. Anti-Bypass: Dapat may source=workink sa URL
    if source != "workink":
        return "BYPASS DETECTED: Go back to the official main link.", 403

    # 2. Anti-Unli: Check kung kakuha lang ng key ang IP na ito
    if ip in already_generated:
        time_passed = time.time() - already_generated[ip]
        if time_passed < REGENERATE_COOLDOWN:
            mins_left = int((REGENERATE_COOLDOWN - time_passed) / 60)
            return f"SPAM PROTECTION: Please wait {mins_left} minutes before generating a new key.", 429

    t = str(uuid.uuid4())
    tokens[t] = {"time": time.time(), "ip": ip}
    return t

@app.route("/getkey")
def getkey():
    cleanup()
    token_input = request.args.get("token")
    ip = request.remote_addr

    # Check kung valid at hindi pa nagagamit ang token
    if not token_input or token_input not in tokens:
        return jsonify({"status": "error", "message": "Token Invalid or Already Used. Go back to main link."}), 403
    
    if tokens[token_input]["ip"] != ip:
        return jsonify({"status": "error", "message": "IP Mismatch. Don't use VPN/Proxy."}), 403

    # BURAHIN AGAD ANG TOKEN PARA HINDI MA-UNLI REFRESH (One-time use only)
    del tokens[token_input] 
    
    # I-LOG ANG IP PARA SA COOLDOWN
    already_generated[ip] = time.time()

    # Generate the actual key
    key = "KazeKey-" + uuid.uuid4().hex[:10].upper()
    keys[key] = {"expiry": time.time() + KEY_EXPIRY, "device": None}

    return jsonify({"status": "success", "key": key})

@app.route("/verify")
def verify():
    key = request.args.get("key")
    device = request.args.get("device")

    if not key or key not in keys:
        return "invalid"

    data = keys[key]

    # Check kung expired na ang key
    if time.time() > data["expiry"]:
        return "expired"

    # Device ID binding (HWID Lock)
    if data["device"] is None:
        data["device"] = device
        return "valid"

    if data["device"] == device:
        return "valid"

    return "locked"

if __name__ == "__main__":
    # Render Dynamic Port logic
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
