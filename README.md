# Zen - Reflective Daily Journal
One day hackathon

## Architecture

<img width="4318" height="1531" alt="image" src="https://github.com/user-attachments/assets/bd470d4e-c1b5-43c9-830f-e5c609207ea5" />

```
/journal-app
│
├── /client/                            # React frontend
│   ├── /public/
│   └── /src/
│       ├── /components/
│       │   ├── JournalForm.jsx         # Input form (text/image/audio)
│       │   ├── JournalEntryList.jsx    # Displays entries
│       │   └── ChatBox.jsx             # Chat UI with Gemini
│       ├── /pages/
│       │   ├── Home.jsx                # Main journal view
│       │   └── Chat.jsx                # Chat with past self
│       ├── /api/
│       │   ├── journal.js              # Axios calls to /api/journal
│       │   └── chat.js                 # Axios calls to /api/chat
│       ├── App.jsx
│       └── index.jsx
│   └── package.json
│
├── /server/                            # Node + Express backend
│   ├── /models/
│   │   └── JournalEntry.js             # MongoDB journal schema
│   ├── /routes/
│   │   ├── journalRoutes.js            # POST/GET /api/journal
│   │   └── chatRoutes.js               # POST /api/chat
│   ├── /controllers/
│   │   ├── journalController.js        # Handle journal logic
│   │   └── chatController.js           # Call Gemini with context
│   ├── /services/
│   │   ├── ocrService.js               # Tesseract OCR
│   │   └── transcriptionService.js     # Transcribe audio
│   ├── /mock/
│   │   └── seed.js                     # Run `node seed.js` to insert mock data
│   ├── app.js                          # Main Express entry
│   └── .env                            # Env vars (MONGO_URI, GEMINI_API_KEY)
│
├── /uploads/                           # (optional) temp file store
│
├── package.json                        # Backend package.json
└── README.md

```
