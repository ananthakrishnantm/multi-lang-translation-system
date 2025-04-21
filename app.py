from flask import Flask, jsonify, request, render_template, redirect, url_for
import requests
from flask_cors import CORS
import logging
import time
import threading
from dotenv import load_dotenv
import queue

import sqlite3
import grpc
import translation_pb2
import translation_pb2_grpc
import os
import xml.etree.ElementTree as ET
from datetime import datetime

app = Flask(__name__)
CORS(app)

load_dotenv()

# Azure Translator API credentials
API_KEY = os.getenv("AZURE_API_KEY")
ENDPOINT = os.getenv("AZURE_ENDPOINT")
LOCATION = os.getenv("AZURE_LOCATION")
XML_SERVICE_URL = "http://127.0.0.1:5001/process_xml"
GRPC_SERVER_ADDRESS = 'localhost:5002'


logging.basicConfig(level=logging.DEBUG)
DB_FILE = 'translations.db'

# gRPC Constants

translation_queue = queue.Queue()

def delete_and_recreate_db():
    try:
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
            print(f"{DB_FILE} has been deleted.")
        
        init_db()
        print("New database has been created.")
    except Exception as e:
        print(f"Error: {e}")

PACKET_SIZE = 1024
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS translations (
            client_id TEXT PRIMARY KEY,
            original_text TEXT,
            translated_text TEXT,
            target_language TEXT,
            status TEXT,
            start_time TEXT,
            completion_time TEXT,
            time_remaining INTEGER,
            packet_count INTEGER,
            packets_processed INTEGER,
            xml_processed BOOLEAN,
            xml_processed_text TEXT,
            grpc_processed BOOLEAN,
            grpc_processed_text TEXT
        )
    ''')
    conn.commit()
    conn.close()

delete_and_recreate_db()

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def send_log_to_sidecar(client_id, message):
    try:
        sidecar_url = "http://127.0.0.1:5002/log"
        payload = {"client_id": client_id, "message": message}
        response = requests.post(sidecar_url, json=payload)
        response.raise_for_status()
    except Exception as e:
        logging.error(f"Failed to send log to sidecar: {e}")


def process_xml(text):
    try:
        root = ET.Element("translation")
        text_elem = ET.SubElement(root, "text")
        text_elem.text = text
        xml_data = ET.tostring(root, encoding='unicode', method='xml')
        response = requests.post(
            XML_SERVICE_URL,
            data=xml_data,
            headers={"Content-Type": "application/xml"}
        )
        response.raise_for_status()
        response_root = ET.fromstring(response.text)
        return response_root.find('.//text').text
    except Exception as e:
        logging.error(f"XML processing error: {e}")
        raise

def process_grpc(text):
    try:
        with grpc.insecure_channel(GRPC_SERVER_ADDRESS) as channel:
            stub = translation_pb2_grpc.TranslationServiceStub(channel)
            request = translation_pb2.TranslateRequest(french_text=text)
            response = stub.TranslateFrenchToEnglish(request)
            return response.english_text
    except Exception as e:
        logging.error(f"gRPC processing error: {e}")
        raise


def save_state(client_id, state):
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO translations 
        (client_id, original_text, translated_text, target_language, status, 
         start_time, completion_time, time_remaining, packet_count, packets_processed,
         xml_processed, xml_processed_text, grpc_processed, grpc_processed_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        client_id,
        state.get('original_text', ''),
        state.get('translated_text', ''),
        state.get('target_language', ''),
        state.get('status', ''),
        state.get('start_time', ''),
        state.get('completion_time', ''),
        state.get('time_remaining', 0),
        state.get('packet_count', 0),
        state.get('packets_processed', 0),
        state.get('xml_processed', False),
        state.get('xml_processed_text', ''),
        state.get('grpc_processed', False),
        state.get('grpc_processed_text', '')
    ))
    conn.commit()
    conn.close()

def load_state(client_id):
    conn = get_db()
    c = conn.cursor()
    result = c.execute('SELECT * FROM translations WHERE client_id = ?', (client_id,)).fetchone()
    conn.close()
    if result:
        return dict(result)
    return None

def process_translation(client_id, text, target_language):
    try:
        packets = [text[i:i + PACKET_SIZE] for i in range(0, len(text), PACKET_SIZE)]
        total_packets = len(packets)
        state = {
            "status": "Processing",
            "original_text": text,
            "translated_text": "",
            "target_language": target_language,
            "start_time": datetime.now().isoformat(),
            "time_remaining": 45,
            "packet_count": total_packets,
            "packets_processed": 0,
            "xml_processed": False,
            "xml_processed_text": "",
            "grpc_processed": False,
            "grpc_processed_text": ""
        }

        save_state(client_id, state)

      

        translated_packets = []
        for i, packet in enumerate(packets):
            headers = {
                "Ocp-Apim-Subscription-Key": API_KEY,
                "Ocp-Apim-Subscription-Region": LOCATION,
                "Content-Type": "application/json"
            }
            body = [{"text": packet}]
            url = f"{ENDPOINT}translate?api-version=3.0&to={target_language}"
            response = requests.post(url, headers=headers, json=body)
            response.raise_for_status()
            translated_packets.append(response.json()[0]["translations"][0]["text"])

            state = load_state(client_id)
            state["packets_processed"] = i + 1
            save_state(client_id, state)

        #final transaltion
        final_translation = ''.join(translated_packets)

        #xml processing of text
        xml_processed_text = process_xml(final_translation)

        #grpc processing
        grpc_processed_text = process_grpc(final_translation)

        #sending to the logs to the sidecar
        send_log_to_sidecar(client_id, f"Translation completed for client {client_id}")

        state = load_state(client_id)
        state.update({
            "status": "Completed",
            "translated_text": final_translation,
            "xml_processed_text": xml_processed_text,
            "grpc_processed_text": grpc_processed_text,
            "completion_time": datetime.now().isoformat(),
            "xml_processed": True,
            "grpc_processed": True,
            "time_remaining": 0
        })

        save_state(client_id, state)

    except Exception as e:
        logging.error(f"Error during translation for client {client_id}: {e}")
        error_state = {
            "status": "Error",
            "original_text": text,
            "translated_text": str(e),
            "target_language": target_language,
            "completion_time": datetime.now().isoformat(),
            "xml_processed": False,
            "grpc_processed": False,
            "time_remaining": 0
        }
        save_state(client_id, error_state)



def queue_worker():
    global status_message
    while True:
        if not translation_queue.empty():
            status_message = "Processing translation"
            client_id,text,target_language = translation_queue.get()
            time.sleep(45)
            process_translation(client_id, text, target_language)
            translation_queue.task_done()
      
        if translation_queue.empty():
            status_message = "Queue is empty"

# Start the queue worker thread
threading.Thread(target=queue_worker, daemon=True).start()

@app.route("/translate", methods=["POST"])
def translate():
    try:
        client_id = request.form.get("client_id")
        text = request.form.get("text", "")
        target_language = request.form.get("target_language", "")

        if not all([client_id, text, target_language]):
            return jsonify({"error": "Missing required fields"}), 400
        

        translation_queue.put((client_id, text, target_language))

        # threading.Thread(target=process_translation, args=(client_id, text, target_language)).start()
        # return redirect(url_for("index"))

        status_message="Each request takes 45s"

        return redirect(url_for("index",status_message=status_message))

    except Exception as e:
            logging.error(f"Error in translation endpoint: {e}")
            return jsonify({"error": str(e)}), 500



@app.route("/status/<client_id>", methods=["GET"])
def get_translation_status(client_id):
    state = load_state(client_id)
    if not state:
        return jsonify({"error": "Client ID not found"}), 404
    return jsonify(state)


@app.route("/status_message", methods=["GET"])
def get_status_message():
    return jsonify({"status_message": status_message})



@app.route("/")
def index():
    conn = get_db()
    c = conn.cursor()
    states = c.execute('SELECT * FROM translations').fetchall()
    conn.close()
    client_states = {row['client_id']: dict(row) for row in states}

    status_message = request.args.get('status_message', '')

    return render_template("index.html", client_states=client_states,status_message=status_message)

if __name__ == "__main__":
    
    app.run(debug=True, port=5000)
