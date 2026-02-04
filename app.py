from flask import Flask, jsonify, request
from flask_cors import CORS
import sys

# Import your converted script
# (Assuming fs.py has a function we can call, or we just run it)
try:
    import fs
except ImportError:
    print("Could not import fs.py. Make sure it exists.")

app = Flask(__name__)
CORS(app)  # This allows Webflow to talk to us

@app.route('/')
def home():
    return "Hello! The Shannova Algorithm API is running."

@app.route('/run', methods=['POST'])
def run_algorithm():
    # Get data from Webflow
    data = request.json
    print(f"Received data: {data}")

    # --- RUN YOUR ALGO HERE ---
    # If fs.py has a function, call it here.
    # Example: result = fs.my_function(data['input'])
    
    # For now, let's just return a success message to prove it connects
    result = "Algorithm executed successfully (Placeholder)"
    
    return jsonify({
        "status": "success", 
        "result": result,
        "input_received": data
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
