from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Databases sa memory
keys = {}
tokens = {}
# Gagamitin lang natin ang IP cooldown para sa mga nagtatangkang mag-spam ng /token endpoint
token_request_cooldown = {}

TOKEN_EXPIRY = 300 # 5 minutes para hindi sila magmadali sa ads
KEY_EXPIRY = 60 # 24 Hours

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
    ref = request.headers.get("Referer", "")
    ip = request.remote_addr

    # Mahigpit na check: Dapat galing sa Work.ink link mo
    # Link mo: https://work.ink/2mGW/kazehayamodz-free-key
    if "work.ink" not in ref:
        return "ERROR: Access denied. Use the official link.", 403

    # Konting cooldown lang sa pag-generate ng token (5 seconds) para iwas bot
    if ip in token_request_cooldown and time.time() - token_request_cooldown[ip] < 5:
        return "Wait a few seconds.", 429

    t = str(uuid.uuid4())
    tokens[t] = {
        "time": time.time(),
        "ip": ip,
        "verified": True # Markado na galing sa tamang link
    }
    
    token_request_cooldown[ip] = time.time()
    return t

@app.route("/getkey")
def getkey():
    cleanup()
    token_input = request.args.get("token")
    ip = request.remote_addr

    if not token_input or token_input not in tokens:
        return jsonify({"status": "error", "message": "Invalid or Expired Token. Go back to main link."}), 403
    
    data = tokens[token_input]

    if data["ip"] != ip:
        return jsonify({"status": "error", "message": "IP Mismatch. Don't use VPN."}), 403

    # Dahil verified ang token (galing sa /token route na may referer check),
    # rekta bigay na agad ng key. No more 5-minute cooldown!
    del tokens[token_input] 

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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
