import logging
import os
from flask import Flask, jsonify

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    filename="logs/flask.log",
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"message": "PDF Processing API is running"})

if __name__ == "__main__":
    try:
        logger.info("Starting Flask server...")
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        logger.exception("Failed to start Flask server")
        raise