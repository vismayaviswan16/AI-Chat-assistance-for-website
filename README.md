# Chat Assistance for Website

A chat widget that answers visitors' questions using **your own content**, and captures leads when someone wants to be contacted.

**Bring your own AI.** Run it free on your own machine with Ollama or LM Studio, or plug in OpenAI, Anthropic (Claude), Google Gemini, Groq, OpenRouter, or any service that speaks the OpenAI API. You choose in one config file; no code changes.

## How it works

```
Visitor's browser                         Your server
┌────────────────────┐   POST /api/chat   ┌────────────────────────────────┐
│ widget.html        │ ─────────────────► │ server.py (Flask)              │
│ style.css          │                    │  1. find matching chunks of    │
│ script.js          │ ◄───────────────── │     your content (retrieval)   │
└────────────────────┘      reply         │  2. ask the chat model         │
                                          │  3. save lead if email typed   │
 knowledge/*.txt ──► embed.py ──► index.json └──────┬──────────────┬────────┘
                                                    ▼              ▼
                                             chat provider   embedding provider
                                             (your choice)   (or keyword search)
```

Your `.txt` files are split into chunks once; each question retrieves only the most relevant chunks, and the model answers from those. The assistant never invents prices or promises and points people to your team when unsure.

## Choose your AI

You make **two** choices in `.env`: which model writes the answers (**chat**) and how the assistant finds the right part of your content (**retrieval**).

### Chat provider (`CHAT_PROVIDER`)

| Provider | Needs | Notes |
| --- | --- | --- |
| `ollama` (default) | Ollama installed, `ollama pull <model>` | Free, private, runs locally |
| `lmstudio` | LM Studio with its local server started | Free, private, runs locally |
| `openai` | `OPENAI_API_KEY` | Paid |
| `anthropic` | `ANTHROPIC_API_KEY` | Claude models, paid |
| `gemini` | `GEMINI_API_KEY` | Google, paid/free tier |
| `groq`, `openrouter` | `GROQ_API_KEY` / `OPENROUTER_API_KEY` | Hosted open models; OpenRouter offers many providers behind one key |
| `custom` | `CHAT_BASE_URL` (+ `CHAT_API_KEY` if required) | Anything OpenAI-compatible: vLLM, Together, Mistral, DeepSeek, a company gateway... |

Set `CHAT_MODEL` to a model name from that service (for example `qwen3:4b` for Ollama). Model names change often, so copy the current one from your provider's documentation. `.env.example` has a ready-to-uncomment block for each provider.

### Retrieval (`EMBED_PROVIDER`)

| Option | What it does | When to pick it |
| --- | --- | --- |
| `keyword` | Word matching (BM25). **No AI model needed.** | Simplest setup; works with every chat provider. Matches words, not meaning, so write your knowledge files with the words visitors use ("pricing", "cost", "price"). |
| `ollama` | Meaning-based search with a local embedding model | You use Ollama anyway. Understands that "cost" means "pricing". |
| `openai`, `gemini`, `openrouter`, `lmstudio`, `custom` | Meaning-based search with a hosted/other embedding model | Best quality for large knowledge bases. Set `EMBED_MODEL`. |

If you don't set `EMBED_PROVIDER`: Ollama chat users get Ollama embeddings, everyone else gets `keyword` (Anthropic, for example, has no embeddings API).

> After changing any `EMBED_*` setting or editing `knowledge/*.txt`, run `python embed.py` again. The server refuses to start if the index was built with different settings than `.env`, so you can't silently get bad answers.

### Example setups

**Fully free and private**

```env
CHAT_PROVIDER=ollama
CHAT_MODEL=qwen3:4b
EMBED_PROVIDER=ollama
EMBED_MODEL=nomic-embed-text
```

**Claude, with no extra embedding service**

```env
CHAT_PROVIDER=anthropic
CHAT_MODEL=claude-haiku-5-5
ANTHROPIC_API_KEY=sk-ant-...
EMBED_PROVIDER=keyword
```

**OpenAI for both**

```env
CHAT_PROVIDER=openai
CHAT_MODEL=<model from your OpenAI account>
OPENAI_API_KEY=sk-...
EMBED_PROVIDER=openai
```

## Quick start

**1. Install dependencies**

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` includes the SDK for every supported provider. You only need the ones you use, so feel free to delete the others.

**2. Configure**

```bash
cp .env.example .env                     # choose your AI, set security options
cp company.example.json company.json     # company name, greeting, contact details
```

Open `.env`, uncomment the block for your provider and fill it in. If you chose Ollama, also run `ollama pull <chat model>` (and `ollama pull nomic-embed-text` for embeddings).

**3. Add your content**

Put plain `.txt` files in a `knowledge/` folder (services, FAQs, about, contact info...). Separate topics with blank lines. Then build the index:

```bash
python embed.py
```

**4. Run the server**

```bash
python server.py
```

On start it prints which chat model and retrieval method it is using, and exits with a clear message if something is missing (an API key, a model name...).

**5. Open the widget**

Serve the `public/` folder, for example `cd public && python -m http.server 8000`, then visit `http://localhost:8000/widget.html`.

## Adding the widget to your website

Copy the `<div id="hc-widget-root">...</div>` block from `public/widget.html` into your page, load `style.css` in `<head>`, and add `<script src="script.js"></script>` before `</body>`. In `script.js`, change `API_BASE` to your deployed server's address.

## Lead capture

When a visitor wants to be contacted, the assistant asks for their name and email. When they type it, the server saves it to `leads.jsonl` (git-ignored) and, if configured, emails you. This is done by the server, not by a model feature, so it behaves identically with every provider and even with small models.

Name and interest are picked up from the conversation ("my name is Jane Doe" and the message where they asked for a quote), so they're best-effort. The email is always exact.

## Cost and safety when using a paid provider

- Set `DAILY_CHAT_LIMIT` to cap total chats per day across all visitors. At the limit, the widget tells visitors to contact you directly.
- Set `CHAT_MAX_TOKENS` to cap the length (and cost) of each answer.
- Per-visitor rate limits (`CHAT_RATE_LIMIT`) are on by default, and messages are capped at 500 characters.
- Set `ALLOWED_ORIGINS=https://yourwebsite.com` so other sites can't use your API key through your server.
- Also set a spending limit in your provider's dashboard. That is the real safety net.
- API keys live only in `.env` on your server. They are never sent to the browser.

## Deploying

1. Run `server.py` where it can reach your chosen provider (and Ollama, if you use it, with enough RAM for the model).
2. Set `ALLOWED_ORIGINS`, and `BEHIND_PROXY=1` if you use a reverse proxy such as nginx.
3. Put HTTPS in front, and set `API_BASE` in `script.js` to that HTTPS address.
4. `server.py` uses `waitress`, a production-grade server, when it is installed (it is in `requirements.txt`).

## Troubleshooting

| Message | Fix |
| --- | --- |
| `Setup problem: ... needs CHAT_MODEL set` | Add `CHAT_MODEL=` for that provider in `.env` |
| `Setup problem: ... needs an API key` | Add the key to `.env` (see the provider table) |
| `The 'openai' package is not installed` | `pip install openai` (or `pip install -r requirements.txt`) |
| `index.json was built with ... but .env now says ...` | Run `python embed.py` again |
| Bot says "I'm not sure" too often | Lower `MIN_SCORE` (embeddings) or `MIN_KEYWORD_COVERAGE` (keyword), or reword your knowledge files |
| Bot drifts off-topic | Raise those values |
| Widget shows "Something went wrong" | Check the server console. The real error (wrong model name, bad key, provider down) is logged there |

## Adding another provider

Everything provider-specific lives in `providers.py`. To add a service that isn't OpenAI-compatible, write a small class with a `chat(system, messages)` method (and optionally `embed(texts, kind)`), then register it in `build_chat_provider()` / `build_embedder()`. Nothing else changes.

## Privacy

Leads (email, name, interest) are stored in `leads.jsonl`. Make sure your privacy policy covers this and delete entries when people ask. With a hosted provider, visitors' messages and the matching chunks of your content are sent to that provider, so review its data policy. With Ollama or LM Studio nothing leaves your server. The widget shows a short notice about how emails are used; adjust it in `widget.html`.

## Project structure

```
server.py            Flask API: sessions, leads, rate limits
providers.py         Chat + embedding adapters (Ollama, OpenAI-compatible, Anthropic)
retrieval.py         Finds relevant chunks (embedding search or keyword/BM25)
embed.py             Builds index.json from knowledge/*.txt
company.json         Your company details (copy of company.example.json)
knowledge/           Your content as .txt files
public/              The widget (widget.html, style.css, script.js)
```

## License

MIT
