# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import json
import re
import time
import html
import requests # HTTP istekleri icin
import resend


basedir = os.path.abspath(os.path.dirname(__file__))
# Lokalde kaggle.json varsa onu kullan; Vercel'de KAGGLE_API_TOKEN (kaggle 2.x) env degiskeni yeterli.
if os.path.exists(os.path.join(basedir, "kaggle.json")):
    os.environ["KAGGLE_CONFIG_DIR"] = basedir

load_dotenv(os.path.join(basedir, ".env"), override=True)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("SECRET_KEY ortam degiskeni tanimli degil (.env dosyasina ekleyin).")

# Vercel proxy'si arkasinda dogru sema (https) ve host bilgisini almak icin
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config.update(
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("VERCEL") == "1",  # lokalde http ile de calissin
)

#======================================================================
# 1. TUM VERILER `data.json` DOSYASINDAN YUKLENIYOR
#======================================================================

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_portfolio_data",
            "description": "Fetch specific information about Vedat's projects, skills, or background from the local database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "data_type": {
                        "type": "string",
                        "enum": ["projects", "skills", "experience", "education"],
                        "description": "The category of information needed."
                    }
                },
                "required": ["data_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_contact_email",
            "description": "Call this when the user wants to leave a message or contact Vedat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sender_name": {"type": "string"},
                    "sender_email": {"type": "string"},
                    "message_content": {"type": "string"}
                },
                "required": ["sender_name", "sender_email", "message_content"]
            }
        }
    }
]


# Veri degiskenlerini global olarak tanimla
MENU_ITEMS = []
LANGUAGE_NAMES = {}
TRANSLATIONS = {}
PROJECTS = {}
SKILLS = {}


def load_data_from_json():
    global MENU_ITEMS, LANGUAGE_NAMES, TRANSLATIONS, PROJECTS, SKILLS
    try:
        with open(os.path.join(basedir, 'data.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        MENU_ITEMS = data.get("MENU_ITEMS", [])
        LANGUAGE_NAMES = data.get("LANGUAGE_NAMES", {})
        TRANSLATIONS = data.get("TRANSLATIONS", {})
        SKILLS = data.get("SKILLS", {})

        # PROJELERİ BURADAN ÇEKİYORUZ:
        # JSON yapında projeler TRANSLATIONS'ın içinde dil bazlı tutuluyor.
        # Eğer özel bir PROJECTS anahtarı yoksa hata vermemesi için:
        PROJECTS = data.get("PROJECTS", {}) 

        # Log uyarılarını susturmak için kontrolü dile göre yapalım
        if not PROJECTS and TRANSLATIONS:
             print("Bilgi: Projeler TRANSLATIONS içinden dinamik olarak okunacak.")
             # İstersen PROJECTS değişkenini burada doldurabilirsin:
             PROJECTS = {lang: content.get("projects", []) for lang, content in TRANSLATIONS.items()}

    except Exception as e:
        print(f"Hata: {e}")

# Uygulama basladiginda verileri yukle
load_data_from_json()



#======================================================================
# 2. CONTEXT PROCESSOR 
#======================================================================

@app.context_processor
def inject_global_vars():
    lang_code = session.get('lang', 'en')
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS.get('en', {}))
    return dict(
        menu=MENU_ITEMS,
        lang=lang_code,
        texts=current_texts,
        language_names=LANGUAGE_NAMES
    )

#======================================================================
# 3. DIL YONETIMI VE SAYFA ROUTE'LARI 
#======================================================================

@app.before_request
def ensure_lang_in_session():
    if 'lang' not in session:
        session['lang'] = 'en'

@app.route("/set_language/<lang_code>")
def set_language(lang_code):
    if lang_code in LANGUAGE_NAMES:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('home'))


def get_portfolio_data(data_type):
    lang_code = session.get('lang', 'en')
    # Use global TRANSLATIONS and SKILLS loaded at app start
    
    try:
        # 1. Projects search
        if data_type == "projects":
            content = TRANSLATIONS.get(lang_code, {}).get("projects", [])
            return json.dumps(content, ensure_ascii=True)
            
        # 2. Skills search
        elif data_type == "skills":
            content = SKILLS.get(lang_code, [])
            return json.dumps(content, ensure_ascii=True)
            
        # 3. Experience search
        elif data_type == "experience":
            content = TRANSLATIONS.get(lang_code, {}).get("experience", [])
            return json.dumps(content, ensure_ascii=True)

        # 4. Education & Certificates search
        elif data_type == "education":
            edu = TRANSLATIONS.get(lang_code, {}).get("education", [])
            cert = TRANSLATIONS.get(lang_code, {}).get("certificates", [])
            return json.dumps({"education": edu, "certificates": cert}, ensure_ascii=True)

    except Exception as e:
        print(f"DEBUG - Data Fetch Error: {e}")
        return "System could not retrieve the data."
        
    return "No information found for this category."

SYSTEM_PROMPT = (
    "You are a friendly assistant on Vedat Koylahisar's personal portfolio website. "
    "You can greet visitors, exchange small talk, and respond in whatever language the user prefers. "
    "Your main purpose is to answer questions about Vedat: his projects, skills, work experience, education, and certificates. "
    "You can also help visitors send Vedat a message by collecting their name, email, and message, then calling 'send_contact_email'. "
    "Before calling 'send_contact_email', make sure you have all three and that the email looks valid. "
    "Use 'get_portfolio_data' to fetch Vedat's information when needed. "
    "However, you are NOT a general-purpose AI. Politely decline requests that have nothing to do with Vedat, such as: "
    "math calculations, coding help, debugging, weather, news, recipes, jokes, writing essays, or any other off-topic task. "
    "When declining, be brief and friendly — redirect the conversation back to Vedat naturally, without sounding robotic or repeating the same phrase every time. "
    "CRITICAL: Never write template placeholders like [Company], [technology], [certificate] or similar bracketed filler text. "
    "Only state concrete facts that came from 'get_portfolio_data' results already in this conversation, or call the tool first if you don't have them yet. "
    "If you genuinely don't have a piece of information, say so plainly instead of inventing a placeholder. "
    "The chat window shows plain text only: do not use Markdown tables, headings, or bold markers. "
    "Keep answers short and conversational; use simple '-' bullet lines for lists."
)

# Sohbet gecmisi tarayicida tutuluyor (Flask session cookie'si 4 KB siniri yuzunden
# tool sonuclarini tasiyamiyordu). Istemciden gelen gecmisi bu sinirlarla temizliyoruz.
MAX_HISTORY_MESSAGES = 12
MAX_MESSAGE_CHARS = 2000


def sanitize_history(raw_history):
    history = []
    if not isinstance(raw_history, list):
        return history
    for item in raw_history[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            history.append({"role": role, "content": content[:MAX_MESSAGE_CHARS]})
    return history


@app.route("/chat", methods=['POST'])
def chat():
    body = request.get_json(silent=True) or {}
    user_msg = str(body.get('message', '')).strip()[:MAX_MESSAGE_CHARS]
    if not user_msg:
        return jsonify({'error': 'No message provided'}), 400

    api_url = os.getenv('CUSTOM_API_BASE', '').rstrip('/')
    if not api_url.endswith('/chat/completions'):
        api_url = f"{api_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {os.getenv('CUSTOM_API_KEY')}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += sanitize_history(body.get('history'))
    messages.append({"role": "user", "content": user_msg})

    try:
        # Model art arda birden fazla tool cagirabilir (once skills, sonra experience gibi),
        # bu yuzden tool_calls bitene kadar dongude devam ediyoruz. 'tools' her adimda
        # gonderilmezse bazi saglayicilar (orn. Groq) modelin tekrar tool cagirmasini
        # hata sayip 400 donuyor.
        MAX_TOOL_ITERATIONS = 5
        response_msg = None

        for _ in range(MAX_TOOL_ITERATIONS):
            payload = {
                "model": os.getenv("CUSTOM_MODEL_NAME"),
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.3
            }
            response = requests.post(api_url, json=payload, headers=headers, timeout=90)
            response.raise_for_status()
            response_msg = response.json()['choices'][0]['message']
            messages.append(response_msg)

            if not response_msg.get("tool_calls"):
                break

            for tool_call in response_msg["tool_calls"]:
                func_name = tool_call["function"]["name"]
                try:
                    args = json.loads(tool_call["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                print(f"DEBUG - Executing: {func_name}")

                if func_name == "get_portfolio_data":
                    result_content = get_portfolio_data(args.get('data_type'))
                elif func_name == "send_contact_email":
                    result_content = send_contact_email(
                        name=args.get('sender_name'),
                        email=args.get('sender_email'),
                        message=args.get('message_content')
                    )
                else:
                    result_content = "Function not found."

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": func_name,
                    "content": str(result_content)
                })

        return jsonify({'reply': response_msg.get('content') or "..."})

    except requests.exceptions.Timeout:
        print("DEBUG - Timeout hatası")
        return jsonify({'reply': "The server took too long to respond. Please try again."}), 504
    except requests.exceptions.RequestException as e:
        print(f"DEBUG - Request Error: {str(e)}")
        return jsonify({'reply': "Connection error. Please try again."}), 500
    except Exception as e:
        print(f"DEBUG - Fatal Error: {str(e)}")
        return jsonify({'reply': "Something went wrong. Let's try again."}), 500


KAGGLE_CACHE_TTL = 3600  # saniye
_kaggle_cache = {"time": 0, "data": []}


def fetch_kaggle_projects():
    # Her /portfolio isteginde Kaggle API'ye gitmemek icin sonucu onbellekte tutuyoruz.
    if _kaggle_cache["data"] and time.time() - _kaggle_cache["time"] < KAGGLE_CACHE_TTL:
        return _kaggle_cache["data"]

    try:
        # kaggle paketi import aninda authenticate() cagiriyor; kimlik bilgisi yoksa
        # tum uygulama cokmesin diye import burada yapiliyor.
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()

        username = os.getenv("KAGGLE_USERNAME") or "vedatkoylahisar"

        # 100 projeye kadar çek, tarihe göre sırala
        kernels = api.kernels_list(user=username, page_size=100, sort_by='dateRun')
        kernels = list(kernels)

        projects = []
        for k in kernels:
            # kaggle 1.x 'isPrivate', 2.x (kagglesdk) 'is_private' kullaniyor
            if getattr(k, 'is_private', False) or getattr(k, 'isPrivate', False):
                continue

            # Açıklama kontrolü
            desc = getattr(k, 'description', None)

            projects.append({
                "title": getattr(k, 'title', 'Untitled'),
                "description": desc,
                "url": f"https://www.kaggle.com/code/{username}/{k.ref.split('/')[-1]}"
            })
        _kaggle_cache.update(time=time.time(), data=projects)
        return projects
    except Exception as e:
        print("Kaggle API error:", e)
        return _kaggle_cache["data"]


# --- Sayfa Route'lari  ---
@app.route("/")
def home():
    return render_template("index.html", active='home')

@app.route("/about")
def about():
    lang_code = session.get('lang', 'en')

    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])
    current_skills_data = SKILLS.get(lang_code, SKILLS["en"])
    current_skills_intro = current_texts.get("skillsIntro", "")  

    return render_template(
        "about.html",
        active='about',
        texts=current_texts,
        skills=current_skills_data,
        skillsIntro=current_skills_intro 
    )




@app.route("/articles")  # Burası URL adresi
def articles():           # BURASI ÖNEMLİ: Fonksiyon ismi 'articles' olmalı
    return render_template("services.html", active='articles')

@app.route("/portfolio")
def portfolio():
    lang_code = session.get('lang', 'en')
    
    # 1. O dile ait genel çevirileri çek (Menü, başlıklar vb. için)
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])

    # 2. Yerel projeleri (JSON içindeki 'projects' listesinden) al
    # DİKKAT: Artık PROJECTS global değişkeninden değil, current_texts içinden alıyoruz
    projects_from_json = current_texts.get("projects", [])
    
    # 3. Kaggle verilerini çek
    kaggle_list = fetch_kaggle_projects()

    # 4. Klasör yapısını oluştur (Kaggle Projeleri Varsa)
    if kaggle_list:
        # Klasör kartı için dil ayarları (Burayı hardcode bırakabiliriz veya JSON'a taşıyabilirsin)
        folder_texts = {
            "tr": {
                "title": "Kaggle Projeleri",
                "desc": "Veri bilimi ve makine ogrenimi uzerine son calismalarim.", 
                "tech": "Python, Pandas, NumPy, Scikit-Learn, PyTorch, Matplotlib, Seaborn",
                "btn_text": "Projeleri Incele"  
            },
            "en": {
                "title": "Kaggle Projects",
                "desc": "My latest work on data science and machine learning.",
                "tech": "Python, Pandas, NumPy, Scikit-Learn, PyTorch, Matplotlib, Seaborn",
                "btn_text": "Browse Projects"   
            },
            "de": {
                "title": "Kaggle Projekte",
                "desc": "Meine neuesten Arbeiten zu Data Science und maschinellem Lernen.",
                "tech": "Python, Pandas, NumPy, Scikit-Learn, PyTorch, Matplotlib, Seaborn",
                "btn_text": "Projekte ansehen"  
            }
        }
        
        txt = folder_texts.get(lang_code, folder_texts['en'])
        
        # Kaggle Klasör Objesi
        kaggle_folder = {
            "title": txt["title"],
            "description": txt["desc"], 
            "desc": txt["desc"],      
            "type": "folder",            
            "tech": txt["tech"],         
            "tags": ["Data Science", "Machine Learning", "Python"], # Kartta etiket görünsün diye
            
            # Profil linki (os modülünü import etmeyi unutma veya direkt string yaz)
            "url": "https://www.kaggle.com/vedatkoylahisar", 
            
            # Alt projeler (Modal içinde gösterilecek liste)
            "sub_projects": kaggle_list,

            # Buton Yazısı 
            "custom_btn": txt["btn_text"] 
        }
        
        # Listeyi Birleştir: [Normal Projeler] + [Kaggle Klasörü]
        all_projects = projects_from_json + [kaggle_folder]
    else:
        all_projects = projects_from_json


    print(f"DEBUG: {len(projects_from_json)} JSON projesi ve {len(kaggle_list) if kaggle_list else 0} Kaggle projesi yüklendi.")

    # 5. RETURN
    return render_template(
        'portfolio.html', 
        active='portfolio',
        texts=current_texts,       # HTML'deki menülerin çalışması için ŞART
        projects=all_projects      # Birleştirilmiş liste
    )


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def send_contact_email(name, email, message):
    api_key = os.getenv("RESEND_API_KEY")
    target_email = os.getenv("MAIL_FROM") # Mesajın gideceği kendi mailin

    name = (name or "").strip()[:100]
    email = (email or "").strip()[:254]
    message = (message or "").strip()[:5000]

    if not name or not message:
        return "Error: Name and message are required."
    if not EMAIL_RE.match(email):
        return "Error: The email address is not valid."

    if not api_key or not target_email:
        print("ERROR: RESEND_API_KEY veya MAIL_FROM tanimli degil.")
        return "Error: Mail service is not configured."

    resend.api_key = api_key

    try:
        # Kullanici girdisi HTML'e escape edilmeden konursa maile link/HTML enjekte edilebilir.
        safe_message = html.escape(message).replace("\n", "<br>")
        params = {
            "from": "Portfolio Assistant <onboarding@resend.dev>",
            "to": [target_email],
            "reply_to": email,
            "subject": f"New Message from {name.replace(chr(10), ' ').replace(chr(13), ' ')}",
            "html": f"""
                <h3>New Contact Request</h3>
                <p><strong>Name:</strong> {html.escape(name)}</p>
                <p><strong>Email:</strong> {html.escape(email)}</p>
                <p><strong>Message:</strong><br>{safe_message}</p>
            """
        }

        email_response = resend.Emails.send(params)
        print(f"Resend Success! ID: {email_response}")
        return "Success: Your message has been delivered to Vedat."
    except Exception as e:
        print(f"Resend Error: {str(e)}")
        return "Error: The message could not be sent right now."



@app.route("/contact", methods=["GET", "POST"])
def contact():
    lang_code = session.get('lang', 'en')
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS.get('en', {}))

    if request.method == "POST":
        # Honeypot: insanlar bu gizli alani gormez, botlar doldurur.
        if request.form.get("website"):
            return redirect(url_for('contact'))

        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        # BURASI DEGISTI: Fonksiyonun bekledigi 3 parametreyi gonderiyoruz
        success_msg = send_contact_email(
            name=name,
            email=email,
            message=message
        )

        # send_contact_email "Success..." diye baslayan bir string donuyor
        if success_msg.startswith("Success"):
            msg = current_texts.get("contactSuccess", "Your message has been sent!")
            flash(msg, "success")
        else:
            msg = current_texts.get("contactError", "An error occurred.")
            flash(msg, "error")

        return redirect(url_for('contact'))

    return render_template("contact.html", active='contact')


@app.route("/robots.txt")
def robots_txt():
    body = f"User-agent: *\nAllow: /\nSitemap: {url_for('sitemap_xml', _external=True)}\n"
    return app.response_class(body, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    urls = "".join(
        f"<url><loc>{url_for(item['endpoint'], _external=True)}</loc></url>"
        for item in MENU_ITEMS
    )
    body = ('<?xml version="1.0" encoding="UTF-8"?>'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>')
    return app.response_class(body, mimetype="application/xml")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host='0.0.0.0', port=port, debug=debug_mode)