from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
import time
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) # Para iwas CORS error sa browser

keys = {}
tokens = {}
token_request_cooldown = {}

TOKEN_EXPIRY = 300 
KEY_EXPIRY = 86400 # 24 Hours

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
    return "KAZE SERVER IS ONLINE! 🚀"

@app.route("/token")
def create_token():
    cleanup()
    # Hahanapin natin ang 'source' sa URL imbes na Referer lang
    source = request.args.get("source")
    ref = request.headers.get("Referer", "")
    ip = request.remote_addr

    # Papayagan kung galing sa Work.ink OR kung may tamang source tag
    if "work.ink" not in ref and source != "workink":
        return "ERROR: Access denied. Please use the official link.", 403

    # Anti-Spam: 5 seconds cooldown bago makakuha ng panibagong token
    if ip in token_request_cooldown and time.time() - token_request_cooldown[ip] < 5:
        return "COOLDOWN: Please wait a bit.", 429

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
        return jsonify({"status": "error", "message": "Invalid or Expired Token."}), 403
    
    if tokens[token_input]["ip"] != ip:
        return jsonify({"status": "error", "message": "IP Mismatch."}), 403

    del tokens[token_input] 

    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()
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
