# 🈂️ Translation Microservices Platform

This is a microservices-based text translation platform built with **Flask**, **gRPC**, **SQLite**, and **Azure Translator API**. It demonstrates the use of:

- Background job queuing
- External services for text processing
- gRPC for service communication
- XML data exchange
- Sidecar logging
- SQLite for state persistence

---

## 📦 Project Structure

```bash
.
├── app.py                 # Main Flask app (port 5000)
├── sidecar.py            # Sidecar service for logging & XML uppercase (port 5002)
├── xml_service.py        # XML processor service (reverses text) (port 5001)
├── grpc_server.py        # gRPC server for translating French to English (port 5003 suggested)
├── migrate_db.py         # Script to migrate the SQLite DB
├── templates/
│   └── index.html        # Web UI template
├── uploads/              # Folder for file uploads (if needed)
├── translations.db       # SQLite database
├── translation.proto     # gRPC service definition
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

---

## ⚙️ Requirements

Make sure you have Python 3.8+ installed. Then, install the dependencies:

```bash
pip install -r requirements.txt
```

---

## 🔧 Setup

1. **Set environment variables** in a `.env` file:

```
AZURE_API_KEY=your_azure_api_key
AZURE_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/
AZURE_LOCATION=your-region
```

2. **Run the database migration** to initialize or update the DB schema:

```bash
python migrate_db.py
```

---

## 🚀 Running the Services

Open **separate terminals** for each service.

### 1. Start the XML Processor (Port 5001)

```bash
python xml_service.py
```

### 2. Start the Sidecar Logger (Port 5002)

> ⚠️ Change the gRPC server port if needed to avoid conflict.

```bash
python sidecar.py
```

### 3. Start the gRPC Translation Server (Port 5003 recommended)

```bash
python grpc_server.py
```

Update `GRPC_SERVER_ADDRESS` in `app.py` if the port is changed:

```python
GRPC_SERVER_ADDRESS = 'localhost:5003'
```

### 4. Start the Main Flask App (Port 5000)

```bash
python app.py
```

Then open your browser to:  
[http://localhost:5000](http://localhost:5000)

---

## 🔄 How It Works

1. Users submit text + target language via the UI.
2. The app:
   - Splits text into 1024-byte packets
   - Translates each using Azure Translator
   - Recombines the full translated text
3. Then:
   - Sends it to the **XML Service** to reverse the text
   - Sends it to the **gRPC Service** to translate French to English
4. Results are stored in SQLite and viewable in the browser
5. Logs are sent to the **Sidecar Logger**

---

## 🧪 Testing

- **Translation Status**:  
  `GET /status/<client_id>`

- **System Queue Status**:  
  `GET /status_message`

- **Log Verification**:  
  Check logs printed by the `sidecar.py` terminal

---

## 📑 gRPC Interface

Defined in `translation.proto`:

```proto
service TranslationService {
    rpc TranslateFrenchToEnglish (TranslateRequest) returns (TranslateResponse);
}

message TranslateRequest {
    string french_text = 1;
}

message TranslateResponse {
    string english_text = 1;
}
```

---

## ✅ Example

1. Submit text like:  
   "Bonjour tout le monde"
2. It gets translated, reversed, processed by gRPC, and saved
3. UI shows:
   - Translated text
   - Reversed XML output
   - Final English translation

---

## 🛠️ Dependencies

```txt
Flask==2.3.3
Flask-Cors==3.0.10
requests==2.31.0
grpcio==1.59.0
grpcio-tools==1.59.0
sqlite3==0.0.1
xmltodict==0.13.0
protobuf==4.23.4
```

---

## 📌 Notes

- Make sure ports are not conflicting (especially gRPC and sidecar).
- `translation_queue` has a built-in 45s delay per task (simulate processing time).
- You can enhance the web interface or add authentication if needed.

---

## 📤 Future Improvements

- Dockerize services for easier deployment
- Use a job queue library like Celery or RQ
- Add retry logic & error resilience
- Better UI/UX for viewing translations

---

## 🧠 Author

Built with ❤️ by [Ananthakrishnan]
