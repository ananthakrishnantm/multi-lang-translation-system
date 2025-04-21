from flask import Flask, jsonify, request
import logging
from datetime import datetime
import xml.etree.ElementTree as ET

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

# Log event endpoint
@app.route('/log', methods=['POST'])
def log_event():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid input"}), 400

    client_id = data.get("client_id", "Unknown")
    message = data.get("message", "No message provided")
    timestamp = datetime.now().isoformat()

    logging.info(f"[{timestamp}] Client: {client_id}, Message: {message}")
    return jsonify({"status": "Logged", "timestamp": timestamp}), 200



# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "Sidecar running"}), 200



# Process XML endpoint
@app.route('/uppercase_process_xml', methods=['POST'])
def process_xml():
    try:
        # Parse incoming XML data
        xml_data = request.data
        if not xml_data:
            return jsonify({"error": "No XML data provided"}), 400

        root = ET.fromstring(xml_data)
        text_element = root.find('.//text')

        if text_element is None or not text_element.text:
            return jsonify({"error": "Invalid XML: Missing <text> element"}), 400

        text = text_element.text
        processed_text = text.upper() 

        logging.info(f"Processed XML text: {processed_text}")
        response_xml = f"<translation><text>{processed_text}</text></translation>"
        return response_xml, 200, {"Content-Type": "application/xml"}
    except ET.ParseError as e:
        logging.error(f"XML parsing error: {e}")
        return jsonify({"error": "Invalid XML format"}), 400
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5002, debug=True)
