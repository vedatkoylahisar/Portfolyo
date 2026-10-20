# Portfolyo

My personal portfolio site, live at **[vedatkoylahisar.com.tr](https://vedatkoylahisar.com.tr)**.
A Flask app in three languages (Turkish / English / German) with an AI assistant that answers
questions about my work and can pass messages on to me by email.

```
Browser ──► Flask (Vercel) ──► Groq chat API (OpenAI-compatible, tool calling)
                │                  └─ tools: get_portfolio_data, send_contact_email
                ├──► Kaggle API   (public notebooks, cached 1h)
                └──► Resend       (contact form + chatbot messages)
```

## Stack

Python 3.12 · Flask · Jinja2 · vanilla JavaScript / CSS · Groq (OpenAI-compatible API) ·
Kaggle REST API · Resend · Vercel

## Features

- **AI assistant with tool calling** — the model calls `get_portfolio_data` to fetch my projects,
  skills, experience and education from `data.json` instead of guessing, and `send_contact_email`
  to deliver a visitor's message once it has their name, email and message
- **Three languages** — all UI text and content live in `data.json`; the language is kept in the
  session and switched from the nav bar
- **Kaggle integration** — my public notebooks are fetched from the Kaggle API and shown as a
  folder on the portfolio page
- **Contact form** — sent through Resend, with input escaping, email validation and a honeypot
  field against bots
- **SEO basics** — meta / Open Graph tags, `robots.txt` and `sitemap.xml`

## Project structure

```
app.py               all routes, chatbot loop, Kaggle and email integrations
data.json            translations and content (projects, skills, experience, education)
templates/           Jinja2 pages (base, index, about, portfolio, contact, articles)
static/css, js       styles, chatbot client, project modal
static/files         CVs (Backend, AI/ML)
```

Content changes (a new project, an updated description) only touch `data.json` — every
language has its own copy under `TRANSLATIONS.<lang>`.

## Running it locally

```bash
git clone https://github.com/vedatkoylahisar/Portfolyo.git
cd Portfolyo
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py                  # http://localhost:5000
```

Create a `.env` file in the project root:

| Variable | Used for |
|---|---|
| `SECRET_KEY` | Flask session signing (required — the app won't start without it) |
| `CUSTOM_API_BASE`, `CUSTOM_API_KEY`, `CUSTOM_MODEL_NAME` | OpenAI-compatible chat API (Groq) |
| `RESEND_API_KEY`, `MAIL_FROM` | Sending contact messages; `MAIL_FROM` is the inbox they go to |
| `KAGGLE_API_TOKEN`, `KAGGLE_USERNAME` | Listing Kaggle notebooks (optional — the folder is hidden without it) |
| `FLASK_DEBUG` | Set to `1` for the debug server locally |

## Deployment

Deployed on Vercel, which detects the Flask app automatically; pushing to `master` triggers a new
deployment. The same variables (except `FLASK_DEBUG`) are set in the Vercel project settings.

## Known limitations

Personal project, kept deliberately simple: there is no rate limiting on `/chat`, chat history is
kept in the browser and sent with each request (so it isn't trusted beyond `user`/`assistant`
text), the Kaggle cache is per server instance, and the Articles page is still a placeholder.

## License

The code is available under the [MIT License](LICENSE). The content — my CVs, photo, and the
texts in `data.json` — is personal and not covered by it.
