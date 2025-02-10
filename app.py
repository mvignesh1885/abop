from flask import Flask, render_template, request, jsonify
import subprocess
import os
import webbrowser
from threading import Timer
import json
import sys

app = Flask(__name__)

@app.route('/MainPage')
def index():
    return render_template('index.html')

@app.route('/MainPage/abop')
def abop_page():
    return render_template('abop.html')

@app.route('/run_script', methods=['POST'])
def run_script():
    script_name = request.form.get("script_name")

    if script_name == "move_to_fill":
        script_path = os.path.join(os.getcwd(), "move_to_fill.py")
    else:
        return jsonify({"error": "Invalid script selected"}), 400

    try:
        output = subprocess.check_output(["python", script_path], text=True)
        return jsonify({"output": output})
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/load_utility/<utility>')
def load_utility(utility):
    try:
        return render_template(f"{utility}.html")
    except:
        return "<h2>Not Found</h2>", 404
    
@app.route('/run_move_to_fill', methods=['POST'])
def run_move_to_fill():
    try:
        data = request.get_json()
        print("Received data from UI:", json.dumps(data, indent=2))  # ✅ Debugging log

        required_fields = ["ENVIRONMENT", "STORE_NUMBER", "rx_details", "sell_selected", "move_to_fill_selected", "generate_abop_selected"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        json_data = json.dumps(data)
        script_path = os.path.join(os.getcwd(), "move_to_fill.py")

        # ✅ Add logging for subprocess execution
        print("Executing move_to_fill.py with data:", json_data)

        result = subprocess.run(["python", script_path, json_data], capture_output=True, text=True)

        if result.returncode == 0:
            print("move_to_fill.py executed successfully:", result.stdout.strip())  # ✅ Log success
            return jsonify({"output": result.stdout.strip()})
        else:
            print("Error running move_to_fill.py:", result.stderr.strip())  # ✅ Log failure
            return jsonify({"error": result.stderr.strip()}), 500

    except Exception as e:
        print("Unexpected error:", str(e))
        return jsonify({"error": str(e)}), 500

def open_browser():
    """Open the browser only once after Flask starts"""
    webbrowser.open_new("http://127.0.0.1:5000/MainPage")

if __name__ == '__main__':
    # Prevent opening the browser twice due to Flask's auto-reload
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Timer(1, open_browser).start()  # Open browser after a 1-second delay
    
    app.run(host="127.0.0.1", port=5000, debug=True)