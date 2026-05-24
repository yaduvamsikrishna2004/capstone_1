# Capstone RAG Assistant

Production-style Retrieval-Augmented Generation (RAG) project in Python with multi-channel notifications.

## Features
- Multi-PDF ingestion and chunking
- DOCX + TXT ingestion for web upload flow
- Sentence Transformer embeddings (`all-MiniLM-L6-v2`)
- Chroma persistent vector store with metadata
- RAG answers with Ollama + Llama3
- Channel-aware short summaries (WhatsApp/SMS/Twitter)
- SQLite history with timestamps
- Twilio WhatsApp + SMS notifications
- Gmail SMTP notifications (Google App Password)
- FastAPI REST API for web frontend integration
- Interactive CLI for ingestion, Q&A, history, and notifications

## Project Structure
```text
capstone_rag/
|-- app.py
|-- config.py
|-- requirements.txt
|-- .gitignore
|-- README.md
|-- .env
|-- .env.example
|-- database.py
|-- rag.py
|-- whatsapp.py
|-- sms.py
|-- email_sender.py
|-- twitter_post.py
|-- database/
|   `-- manager.py
|-- rag/
|   `-- pipeline.py
|-- notifications/
|   |-- whatsapp.py
|   |-- sms.py
|   `-- email_sender.py
|-- utils/
|   |-- logger.py
|   `-- text.py
|-- documents/
`-- vector_store/
```

## Architecture Overview
1. **Ingestion**: PDFs are loaded and split into overlapping chunks.
2. **Embeddings**: Chunks are embedded with Sentence Transformers.
3. **Vector Storage**: Chunks + metadata (source, page, chunk index) are stored in Chroma.
4. **Retrieval**: Query embedding retrieves semantically similar chunks.
5. **Generation**: Ollama (Llama3) answers using only retrieved context.
6. **Persistence**: SQLite stores summary history, query history, notification logs.
7. **Notifications**: WhatsApp/SMS/Email are sent with channel-aware summaries.

## Setup
### 1) Clone and install
```bash
git clone <your-repo-url>
cd capstone_rag
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Start Ollama
```bash
ollama serve
ollama pull llama3
```

### 3) Configure environment
Copy `.env.example` to `.env` and fill credentials.

## Usage
Run interactive CLI:
```bash
python app.py
```

Menu supports:
- ingest PDF(s)
- ask questions
- send notifications
- view recent summaries

Run FastAPI server for web UI:
```bash
uvicorn api_server:app --reload --host 127.0.0.1 --port 8000
```

## Gmail SMTP (App Password)
1. Enable Google 2-Step Verification on sender account.
2. Generate App Password in Google Account Security.
3. Set:
   - `EMAIL_ADDRESS=<sender@gmail.com>`
   - `EMAIL_APP_PASSWORD=<16-char app password>`
   - `RECEIVER_EMAIL=<recipient@gmail.com>`

If you get `SMTPAuthenticationError 535`, verify the app password belongs to the same account as `EMAIL_ADDRESS`.

## Twilio Setup
1. Create Twilio account and get SID/Auth token.
2. Enable WhatsApp sandbox (or approved sender).
3. Configure `.env` Twilio numbers and recipient numbers in E.164 format.

## RAG Engineering Notes
- **Embeddings**: numerical vector representation of text semantics.
- **Vector search**: nearest-neighbor search on embeddings.
- **Cosine similarity**: measures directional closeness between vectors.
- **Chunk overlap**: preserves context continuity across chunks.
- **Metadata retrieval**: improves traceability to source document/page.

## Error Handling Included
- missing PDF file
- empty chunk/retrieval results
- Chroma storage/retrieval failures
- Ollama connection/request failures
- Twilio API errors
- Gmail SMTP auth/connectivity errors
- SQLite operation failures

## Testing Suggestions
- **Unit tests**:
  - chunking and summary length limits
  - config and env validation
  - DB read/write helpers
- **Integration tests**:
  - end-to-end ingest -> retrieve -> answer
  - notification dispatch with mocked providers
- **Mocking**:
  - mock Twilio `Client.messages.create`
  - mock `smtplib.SMTP`
  - mock Ollama client responses

## Security Best Practices
- Never commit `.env`.
- Rotate Twilio/Auth/App Password credentials regularly.
- Use separate credentials for dev/prod.
- Prefer cloud secret managers in deployment.
- Add request throttling/rate limits for public APIs.

## Scalability Improvements Included
- batch PDF ingestion
- duplicate-chunk prevention via SHA-256 IDs
- user ID support for per-user history
- query caching for repeated prompts

## Optional Upgrades
- Streamlit web UI
- FastAPI backend + REST endpoints
- Docker + docker-compose
- OCR for scanned PDFs (Tesseract/PaddleOCR)
- Redis caching
- Background jobs (Celery/RQ)
- GPU embedding model acceleration
- LangChain/LlamaIndex agent workflows

## Deployment Recommendations
- **Small demo**: Render/Railway + Ollama on local/GPU machine
- **Production API**: FastAPI + managed Postgres + object storage
- **GPU inference**: run Ollama/model server on dedicated GPU VM
- **Observability**: add Sentry + Prometheus/Grafana + structured logs

## Screenshots (Placeholders)
- `docs/screenshots/cli-menu.png`
- `docs/screenshots/ingestion-report.png`
- `docs/screenshots/query-response.png`
- `docs/screenshots/notification-success.png`

## License
Add your preferred license (MIT recommended for portfolio projects).
