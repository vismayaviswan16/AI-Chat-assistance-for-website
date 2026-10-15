# Website Chat Assistant

A chatbot widget you can add to any website. It answers visitors' questions using your own content, runs fully offline on your machine with [Ollama](https://ollama.com), and can email you the contact details of interested visitors.

**How it works:** your text files in `knowledge/` are turned into embeddings. When a visitor asks a question, the most relevant files are found and given to a local AI model, which writes the answer. A small JavaScript widget shows the chat on your page.

## Features

- Answers only from your own content, with no invented prices or promises
- Runs locally with Ollama, so there are no API keys and no usage fees
- Captures leads and optionally emails them to you
- All company details live in one config file, so no code changes are needed
- Lightweight chat widget (HTML, CSS, JS) you can restyle

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/download) installed and running
- About 4 GB of free RAM for the default model

## Project structure

```
├── server.py              backend (Flask)
├── embed.py               builds index.json from knowledge/
├── requirements.txt
├── company.example.json   template for your company details
├── company.json           your details (private, not in Git)
├── .env.example           template for email settings
├── .env                   your email settings (private, not in Git)
├── knowledge/             your .txt files about your business
└── public/
    ├── widget.html        demo page with the chat widget
    ├── script.js          widget logic
    └── style.css          widget styling
```

## Setup

### 1. Download the project and create a virtual environment

```
git clone https://github.com/vismayaviswan16/Chat-assistance-for-website.git
cd Chat-assistance-for-website
python -m venv venv
```

Activate it:

- Windows: `venv\Scripts\activate`
- macOS / Linux: `source venv/bin/activate`

### 2. Install dependencies

```
pip install -r requirements.txt
```

### 3. Pull the AI models

```
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

### 4. Add your company details

Copy the template and edit your copy:

- Windows: `copy company.example.json company.json`
- macOS / Linux: `cp company.example.json company.json`

Open `company.json` and replace every value that follows a `FILL IN` line with your own: company name, description, services, contact email, phone and greeting.

### 5. Add your knowledge

Create `.txt` files about your business in the `knowledge/` folder. See `knowledge/README.md` for what to write.

- One topic per file (about, services, contact, FAQ, and so on)
- 100 to 300 words each, written in plain sentences
- You need at least one `.txt` file before running `embed.py`

### 6. (Optional) Set up lead emails

If you want an email whenever a visitor asks to be contacted:

- Windows: `copy .env.example .env`
- macOS / Linux: `cp .env.example .env`

Fill in `SENDER_EMAIL`, `SENDER_APP_PASSWORD` and `LEAD_RECIPIENT`. For Gmail, turn on 2-step verification and create an **app password**; do not use your normal password.

Skip this step and leads are only printed in the terminal.

### 7. Build the knowledge index

```
python embed.py
```

Run this again every time you change anything in `knowledge/`.

### 8. Start the server

Make sure Ollama is running, then:

```
python server.py
```

The server runs at `http://127.0.0.1:3000`. Open `public/widget.html` in your browser to try the chat. You can also check `http://127.0.0.1:3000/api/health`.

## Add the widget to your website

1. Open `public/widget.html` and copy everything inside `<div id="hc-widget-root"> ... </div>` into your page, just before `</body>`.
2. Copy `public/style.css` and `public/script.js` to your website, and link them: `<link rel="stylesheet" href="style.css">` in the `<head>`, and `<script src="script.js"></script>` after the widget markup.
3. In `script.js`, set `API_BASE` to your backend's address. Leave it as `http://127.0.0.1:3000` while testing locally.

## Customizing

| What | Where |
|---|---|
| Company name, services, contact details, greeting | `company.json` |
| What the bot knows | `knowledge/*.txt`, then run `python embed.py` |
| Bot rules and behavior | the `Rules:` section in `build_system_prompt` in `server.py` |
| AI model | `CHAT_MODEL` in `.env` (for example `phi4-mini`) |
| Colors and fonts | `public/style.css` (the variables at the top) |
| Header text, subtitle, input placeholder | `public/widget.html` |
| Port and host | `PORT` and `HOST` in `.env` |

## Deploying online

The widget on your website needs to reach the backend, so the backend must be hosted somewhere that can run Ollama and Python. Before going live:

- Set `API_BASE` in `script.js` to your server's HTTPS address.
- Replace `CORS(app)` in `server.py` with `CORS(app, origins=["https://yourwebsite.com"])`.
- Put the server behind HTTPS (for example with a reverse proxy such as Nginx or Caddy).
- Consider adding rate limiting, because every message runs the AI model on your server.

## Troubleshooting

| Problem | Fix |
|---|---|
| `index.json not found` | Run `python embed.py` first |
| `No .txt files found` | Create at least one `.txt` file in the `knowledge/` folder |
| "Something went wrong. Is Ollama running...?" | Start Ollama and make sure both models are pulled |
| Widget says "I couldn't connect" | Check the server is running and `API_BASE` is correct |
| Bot ignores your new content | Run `python embed.py` again, then restart `server.py` |
| Lead email not sent | Check `.env` values; Gmail needs an app password |
| Answers are slow | Use a smaller model, or run Ollama on a machine with a GPU |

## Privacy and security

- Never commit `.env` or `company.json`. They are already listed in `.gitignore`.
- `index.json` contains your knowledge text, so don't publish it if the content is private.
- Visitors' emails are only sent to the address you set in `LEAD_RECIPIENT`.
- Tell your visitors how you use the contact details they share, according to the privacy laws that apply to you.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file.
