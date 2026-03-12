from flask import Flask, request
from flask_cors import CORS
import uuid, time, os

app = Flask(__name__)
CORS(app)

# ======================
# GLOBAL STORAGE
# ======================
keys = {}           # stores generated keys
sessions = {}       # stores session tokens
ip_cooldown = {}    # tracks cooldown per IP

# ======================
# CONFIG
# ======================
TOKEN_EXPIRY = 20      # seconds for session token
COOLDOWN = 60          # seconds cooldown per IP
KEY_EXPIRY = 180       # seconds for key expiry


# ======================
# CLEANUP FUNCTION
# ======================
def cleanup():
    now = time.time()
    # expired session tokens
    expired_tokens = [t for t,d in sessions.items() if now - d["time"] > TOKEN_EXPIRY]
    for t in expired_tokens:
        del sessions[t]
    # expired keys
    expired_keys = [k for k,d in keys.items() if now > d["expiry"]]
    for k in expired_keys:
        del keys[k]


# ======================
# CREATE SESSION TOKEN
# ======================
@app.route("/session")
def create_session():
    cleanup()
    ref = request.headers.get("Referer","")
    ip = request.remote_addr

    # only allow main link or work.ink
    if ("work.ink" not in ref) and ("kaze-key-page.onrender.com" not in ref):
        return "Access denied, go through main link"

    # IP cooldown for session creation (spam prevention)
    if ip in ip_cooldown and time.time() - ip_cooldown[ip] < COOLDOWN:
        remaining = COOLDOWN - (time.time() - ip_cooldown[ip])
        return f"Wait {int(remaining)} seconds before requesting a new session"

    token = str(uuid.uuid4())
    sessions[token] = {"time": time.time(), "ip": ip, "used": False}

    return token


# ======================
# GET KEY (One-time)
# ======================
@app.route("/getkey")
def get_key():
    cleanup()
    token = request.args.get("token")
    ip = request.remote_addr

    if not token or token not in sessions:
        return "Access denied: invalid session, go through main link"

    session = sessions[token]

    # token expired
    if time.time() - session["time"] > TOKEN_EXPIRY:
        del sessions[token]
        return "Session expired"

    # token already used
    if session["used"]:
        return "Session already used"

    # IP mismatch
    if session["ip"] != ip:
        del sessions[token]
        return "Access denied: IP mismatch"

    # mark token as used
    session["used"] = True
    ip_cooldown[ip] = time.time()

    # generate key
    key = "KazeFreeKey-" + uuid.uuid4().hex[:12].upper()
    keys[key] = {"expiry": time.time() + KEY_EXPIRY, "device": None}

    return f"YOUR KEY: {key}"


# ======================
# VERIFY KEY
# ======================
@app.route("/verify")
def verify_key():
    cleanup()
    key = request.args.get("key")
    device = request.args.get("device")

    if not key or key not in keys:
        return "invalid"

    data = keys[key]

    if time.time() > data["expiry"]:
        return "expired"

    # first login bind device
    if data["device"] is None:
        data["device"] = device
        return "valid"

    if data["device"] == device:
        return "valid"

    # different device
    return "locked"


# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
