from flask import Flask, jsonify
import os
import redis

app = Flask(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
KEY = "hits"

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

@app.route("/")
def index():
    try:
        hits = r.incr(KEY)
        return jsonify(status="ok", message="Hello from Flask on K8s!", hits=hits)
    except Exception as e:
        return jsonify(status="error", error=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

