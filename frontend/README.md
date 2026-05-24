# AI Document Assistant Frontend (Vanilla)

Production-style frontend rebuilt from scratch using:

- HTML
- CSS
- Vanilla JavaScript (ES modules)

No React, Vue, Angular, NextJS, Bootstrap, jQuery, Tailwind, or external UI frameworks are used.

## Folder Structure

```text
frontend/
|
|-- index.html
|-- css/
|   |-- main.css
|   |-- sidebar.css
|   |-- chat.css
|   |-- upload.css
|   |-- modal.css
|   `-- responsive.css
|-- js/
|   |-- app.js
|   |-- api.js
|   |-- chat.js
|   |-- upload.js
|   |-- history.js
|   |-- notifications.js
|   |-- theme.js
|   `-- utils.js
`-- assets/
    |-- images/
    |-- icons/
    `-- animations/
```

## Backend Integration

Integrated directly with FastAPI endpoints:

- `GET /health`
- `POST /upload`
- `POST /ask`
- `GET /history`
- `POST /send-email`
- `POST /send-whatsapp`
- `POST /send-sms`

Configured in `js/api.js`:

- Default base URL: `http://localhost:8000`
- Can be changed in UI via `Settings` modal
- Timeout + retry logic is included

## Local Run

1. Start your FastAPI backend:
   - `uvicorn api_server:app --reload --host 127.0.0.1 --port 8000`
2. Serve frontend as static files:
   - From `capstone_rag/frontend`
   - `python -m http.server 5500`
3. Open:
   - `http://127.0.0.1:5500`

## Features Included

- Dark mode default + light/dark toggle with persistence
- Collapsible fixed sidebar with searchable recent chats
- Welcome prompt cards with hover animation
- Drag/drop multi-file upload (PDF, DOCX, TXT)
- Upload queue, statuses, progress bars, remove action
- ChatGPT-style chat alignment and message actions
- Markdown rendering with tables/lists/code blocks
- Syntax highlighting (vanilla implementation)
- Typing indicator + streaming display effect
- Message copy/regenerate/thumb feedback controls
- Expanding textarea with Enter/Shift+Enter behavior
- Right action panel with document metadata and quick actions
- Email/WhatsApp/SMS modal forms with validation and API integration
- Toast notifications, skeleton loading, smooth scrolling
- Server history lazy loading
- Fully responsive desktop/tablet/mobile layout

## Deployment

### Option A: Serve with FastAPI Static Files

You can mount this `frontend/` directory as static files in your FastAPI app and serve `index.html` as the main page.

### Option B: Deploy as Static Site + API

1. Deploy `frontend/` to any static host (Nginx, S3+CloudFront, Netlify, Vercel static).
2. Ensure API CORS allows frontend origin.
3. Set API base URL from Settings modal after first load.

## Production Notes

- Keep backend URL HTTPS in production.
- Add rate limits/auth at API gateway level if exposed publicly.
- Keep Twilio and email credentials only in backend `.env`.
