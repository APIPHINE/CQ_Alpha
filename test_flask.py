import logging
import os
from flask import Flask, jsonify

# Create logs directory
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    filename="logs/test_flask.log",
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/")
def index():
    return jsonify({"message": "Test Flask server is running"})

if __name__ == "__main__":
    try:
        logger.info("Starting test Flask server...")
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        logger.exception("Failed to start test Flask server")
        raise
