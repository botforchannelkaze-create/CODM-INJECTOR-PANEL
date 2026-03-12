from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
# Pinaka-importante: CORS setup para sa browser requests
CORS(app, resources={r"/*": {"origins": "*"}})

keys = {}
tokens = {}
token_request_cooldown = {}

TOKEN_EXPIRY = 300 
KEY_EXPIRY = 60 # Ginawa kong 24 hours (86400s)

def cleanup():
    now = time.time()
    for t in list(tokens.keys()):
        if now - tokens[t]["time"] > TOKEN_EXPIRY:
            del tokens[t]
    for k in list(keys.keys()):
        if now > keys[k]["expiry"]:
            del keys[k]

@app.route("/")
def home():
    return "KAZE SERVER IS ONLINE! 🚀"

@app.route("/token")
def create_token():
    cleanup()
    
    # Kukunin natin ang source sa URL parameter (?source=workink)
    source = request.args.get("source")
    ref = request.headers.get("Referer", "")
    ip = request.remote_addr

    # DEBUG logs sa Render
    print(f"DEBUG: Referer: {ref} | Source: {source} | IP: {ip}")

    # Papayagan kung galing sa Work.ink OR kung may tamang source tag
    if "work.ink" not in ref and source != "workink":
        return "ERROR: Access denied. Please use the official link.", 403

    # Anti-Spam: 5 seconds cooldown bago makakuha ng panibagong token
    if ip in token_request_cooldown and time.time() - token_request_cooldown[ip] < 5:
        return "COOLDOWN: Please wait 5 seconds.", 429

    t = str(uuid.uuid4())
    tokens[t] = {"time": time.time(), "ip": ip}
    token_request_cooldown[ip] = time.time()
    
    return t

@app.route("/getkey")
def getkey():
    cleanup()
    token_input = request.args.get("token")
    ip = request.remote_addr

    if not token_input or token_input not in tokens:
        return jsonify({"status": "error", "message": "Invalid/Expired Token. Restart link."}), 403
    
    data = tokens[token_input]
    if data["ip"] != ip:
        return jsonify({"status": "error", "message": "IP Mismatch. Don't use VPN."}), 403

    del tokens[token_input] 

    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()
    keys[key] = {"expiry": time.time() + KEY_EXPIRY, "device": None}

    return jsonify({"status": "success", "key": key})

@app.route("/verify")
def verify():
    key = request.args.get("key")
    device = request.args.get("device")
    if not key or key not in keys: return "invalid"
    data = keys[key]
    if time.time() > data["expiry"]: return "expired"
    if data["device"] is None:
        data["device"] = device
        return "valid"
    return "valid" if data["device"] == device else "locked"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
