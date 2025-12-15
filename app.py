# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from dotenv import load_dotenv
import json
import requests # HTTP istekleri icin
import smtplib
import re
from email.message import EmailMessage

basedir = os.path.abspath(os.path.dirname(__file__))
os.environ["KAGGLE_CONFIG_DIR"] = basedir

from kaggle.api.kaggle_api_extended import KaggleApi
# .env dosyasindaki degiskenleri yukle
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# === Hugging Face API Ayarlari (Degisiklik Yok) ===
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")

if not HF_API_KEY:
    print("="*50)
    print("HATA: HUGGINGFACE_API_KEY bulunamadi.")
    print("Lutfen .env dosyasini kontrol edin.")
    print("="*50)

#======================================================================
# 1. TUM VERILER `data.json` DOSYASINDAN YUKLENIYOR
#======================================================================

# Veri degiskenlerini global olarak tanimla
MENU_ITEMS = []
LANGUAGE_NAMES = {}
TRANSLATIONS = {}
PROJECTS = {}
SKILLS = {}  # <<< SKILLS değişkeni

with open("chatbot_contact_flow.json", "r", encoding="utf-8") as f:
    CONTACT_FLOW = json.load(f)


def load_data_from_json():
    """data.json dosyasindaki tum verileri global degiskenlere yukler."""
    global MENU_ITEMS, LANGUAGE_NAMES, TRANSLATIONS, PROJECTS, SKILLS
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Global degiskenlere ata
        MENU_ITEMS = data.get("MENU_ITEMS", [])
        LANGUAGE_NAMES = data.get("LANGUAGE_NAMES", {})
        TRANSLATIONS = data.get("TRANSLATIONS", {})
        PROJECTS = data.get("PROJECTS", {})
        SKILLS = data.get("SKILLS", {})

        # Kontrol ve uyarı
        if not TRANSLATIONS:
            print("UYARI: TRANSLATIONS eksik olabilir.")
        if not PROJECTS:
            print("UYARI: PROJECTS eksik olabilir.")
        if not SKILLS:
            print("UYARI: SKILLS eksik olabilir.")
        
        # skillsIntro eksikse boş string olarak ekle
        for lang_code, texts in TRANSLATIONS.items():
            if "skillsIntro" not in texts:
                texts["skillsIntro"] = ""

    except FileNotFoundError:
        print("="*50)
        print("HATA: data.json dosyasi bulunamadi! Lutfen app.py ile ayni dizinde oldugundan emin olun.")
        print("="*50)
    except json.JSONDecodeError:
        print("="*50)
        print("HATA: data.json hatali formatta. Gecerli bir JSON oldugundan emin olun.")
        print("="*50)
    except Exception as e:
        print(f"data.json okunurken beklenmedik bir hata olustu: {e}")

# Uygulama basladiginda verileri yukle
load_data_from_json()



#======================================================================
# 2. CONTEXT PROCESSOR (Degisiklik Yok)
#======================================================================

@app.context_processor
def inject_global_vars():
    # ... (Degisiklik yok) ...
    lang_code = session.get('lang', 'en')
    # Veriler artik global degiskenden geliyor
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS.get('en', {}))
    return dict(
        menu=MENU_ITEMS,
        lang=lang_code,
        texts=current_texts,
        language_names=LANGUAGE_NAMES
    )

#======================================================================
# 3. DIL YONETIMI VE SAYFA ROUTE'LARI (Degisiklik Yok)
#======================================================================

@app.before_request
def ensure_lang_in_session():
    # ... (Degisiklik yok) ...
    if 'lang' not in session:
        session['lang'] = 'en'

@app.route("/set_language/<lang_code>")
def set_language(lang_code):
    # ... (Degisiklik yok) ...
    if lang_code in LANGUAGE_NAMES:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('home'))

# === /CHAT ROTASI (KATI TALIMATLAR ILE HALUSINASYONU ONLER) ===
@app.route("/chat", methods=['POST'])
def chat():
    lang_code = session.get('lang', 'en')
    # Veriler global degiskenden geliyor
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS.get('en', {}))
    error_message = current_texts.get('chat_general_knowledge_decline', 'Sorry, I cannot help with that.')

    if not HF_API_KEY:
        print("Hugging Face API Anahtari eksik.")
        return jsonify({'reply': error_message}), 500

    try:
        user_message = request.json.get('message')
        lang_name = LANGUAGE_NAMES.get(lang_code, 'English')

        if not user_message:
            return jsonify({'error': 'Mesaj bulunamadi'}), 400


        # 1. CV'den gelen SABIT bilgileri al
        vedat_context = current_texts.get("chatbot_context", "")

        # 2. PROJELER'den DINAMIK bilgileri olustur
        project_context = "\n**Key Projects (from website):**\n"
        # Veriler global degiskenden geliyor
        projects_list = PROJECTS.get(lang_code, PROJECTS.get('en', []))
        if projects_list:
            for proj in projects_list:
                project_context += f"  - {proj['title']}: {proj['desc']}\n"
        else:
            project_context = "\n(No projects listed for this language.)\n"
        
        # 3. KATI SISTEM TALIMATI (Halusinasyonu onler)
        system_prompt = f"""
You are a professional portfolio assistant for Vedat Koylahisar. Your name is 'Yapay Zeka Asistani'.
Your primary goal is to answer user questions based *ONLY* on the facts provided below.
You MUST respond in the user's current language: {lang_name}.
You are not a general AI. You do not know the current date, time, weather, or news.
If the user is chatting normally during a contact process,
answer naturally like a chatbot.
Do not repeat contact questions unless it makes sense.


**Strict Rules:**
1. Do not invent or assume any information not listed in the facts.
2. If the user asks a question not covered by the facts (e.g., "what is the date today?", "bugun gunlerden ne?", "what is the weather?", "who won the game?", "what is 2+2?"), you MUST politely decline. 
   - Good response (in {lang_name}): "{current_texts['chat_general_knowledge_decline']}"
   - Bad response: "Today is July 26th."
3. Stick *only* to the provided facts.

---
**Facts about Vedat Koylahisar (from CV/Manual Entry):**
{vedat_context}
---
**Facts about Vedat's Projects (from PROJECTS dictionary):**
{project_context}
---
"""

        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }

        # 4. PAYLOAD'u olustur
        payload = {
            "model": "meta-llama/Llama-3.1-8B-Instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 150,
            "temperature": 0.2 # Yaratıcılık DÜŞÜK
        }

        response = requests.post("https://router.huggingface.co/v1/chat/completions",
                                 headers=headers, json=payload)

        if response.status_code != 200:
            print(f"Hugging Face API Hatasi: {response.status_code} - {response.text}")
            if response.status_code == 503:
                loading_msg = "Model su anda yukleniyor, lutfen birkac saniye sonra tekrar deneyin."
                if lang_code == 'en': loading_msg = "The model is currently loading, please try again in a few seconds."
                elif lang_code == 'de': loading_msg = "Das Modell wird gerade geladen, bitte versuchen Sie es in wenigen Sekunden erneut."
                return jsonify({'reply': loading_msg}), 503
            raise Exception("API request failed")

        data = response.json()
        ai_reply = data['choices'][0]['message']['content'].strip()

        return jsonify({'reply': ai_reply})

    except Exception as e:
        print(f"Chatbot Hata: {e}")
        return jsonify({'reply': error_message}), 500

def fetch_kaggle_projects():
    try:
        api = KaggleApi()
        api.authenticate()

        username = os.getenv("KAGGLE_USERNAME") or "vedatkoylahisar"

        # Son 10 projeyi al
        kernels = api.kernels_list(user=username, page_size=10)
        kernels = list(kernels)  # iterable -> liste

        projects = []
        for k in kernels:
            desc = getattr(k, 'description', None) or "No description provided."
            projects.append({
                    "title": getattr(k, 'title', 'Untitled'),
                    # Description boşsa hiç yazma
                    "description": getattr(k, 'description', None),
                    "url": f"https://www.kaggle.com/code/{username}/{k.ref.split('/')[-1]}",
                    "image": "/static/images/kaggle_logo.png"
                            })
        return projects
    except Exception as e:
        print("Kaggle API error:", e)
        return []


# --- Sayfa Route'lari (Degisiklik Yok) ---
@app.route("/")
def home():
    return render_template("index.html", active='home')

@app.route("/about")
def about():
    lang_code = session.get('lang', 'en')

    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])
    current_skills_data = SKILLS.get(lang_code, SKILLS["en"])
    current_skills_intro = current_texts.get("skillsIntro", "")  # <<< BURASI EKLENDİ

    return render_template(
        "about.html",
        active='about',
        texts=current_texts,
        skills=current_skills_data,
        skillsIntro=current_skills_intro  # <<< BURASI EKLENDİ
    )




@app.route("/services")
def services():
    return render_template("services.html", active='services')

@app.route("/portfolio")
def portfolio():
    lang_code = session.get('lang', 'en')
    
    # Yerel projeleri al (data.json'dan)
    # Eğer lang_code için proje yoksa, default olarak 'en' kullan
    projects_from_json = PROJECTS.get(lang_code, PROJECTS.get('en', []))
    
    # Kaggle projelerini çek (Bu projelerin 'desc' yerine 'description' kullandığını varsayıyoruz)
    kaggle_projects = fetch_kaggle_projects()
    
    # Tüm projeleri birleştir
    all_projects = projects_from_json + kaggle_projects

    # HATA AYIKLAMA (DEBUG) İÇİN: Konsola kaç proje çekildiğini yazdırın
    print(f"DEBUG: {len(projects_from_json)} JSON projesi ve {len(kaggle_projects)} Kaggle projesi çekildi. Toplam: {len(all_projects)}")

    # Eğer all_projects listesi boşsa, şablonunuzda hiçbir şey görünmez.
    return render_template("portfolio.html", active='portfolio', projects=all_projects)


def send_mail(name, email, message):
    msg = EmailMessage()
    msg["Subject"] = "Portfolio Iletisim Mesaji"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS

    msg.set_content(f"""
Yeni bir iletisim mesaji aldin:

Isim: {name}
Gonderen Mail: {email}

Mesaj:
{message}
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)



@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]

        send_mail(name, email, message)

        flash("Mesajiniz basariyla gonderildi.", "success")
        return redirect(url_for("contact"))

    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True)