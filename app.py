# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from dotenv import load_dotenv
import json
import requests # HTTP istekleri icin
import smtplib
import re
from email.message import EmailMessage
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email

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

# ======================================================================
# GUNCEL CHAT ROTASI (Loop Fix + Mail Robustness)
# ======================================================================
@app.route("/chat", methods=['POST'])
def chat():
    # 1. Temel Ayarlar ve Dil
    lang_code = session.get('lang', 'en')
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS.get('en', {}))
    error_message = current_texts.get('chat_general_knowledge_decline', 'Sorry, I cannot help with that.')
    
    # Kullanıcı mesajını al
    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Mesaj bulunamadi'}), 400

    # 2. Durum Kontrolü
    current_state = session.get('chat_state', 'idle')
    ai_reply = ""
    
    # Bu değişken "Hayır" denildiğinde döngüye girmeyi engeller
    force_ai_response = False 

    # ------------------------------------------------------------------
    # ÖZEL DURUM: TEYİT AŞAMASI (CONFIRMING)
    # ------------------------------------------------------------------
    if current_state == 'confirming_contact':
        affirmative = ['evet', 'yes', 'ja', 'onay', 'istiyorum', 'tabii', 'ok', 'hıhı', 'yep']
        negation = ['hayır', 'no', 'nein', 'yok', 'istemiyorum', 'gerek yok', 'kalsın']
        
        msg_lower = user_message.lower()

        # Cevap EVET ise -> İsim sorma adımına geç
        if any(word in msg_lower for word in affirmative):
            session['chat_state'] = 'waiting_name'
            if lang_code == 'tr': ai_reply = "Harika. Öncelikle adınızı öğrenebilir miyim?"
            elif lang_code == 'de': ai_reply = "Super. Darf ich zuerst Ihren Namen erfahren?"
            else: ai_reply = "Great. May I have your name first?"
            return jsonify({'reply': ai_reply})
        
        # Cevap HAYIR ise -> Eski mesajı geri getir ve AI'ya gitmesini ZORLA
        else:
            session['chat_state'] = 'idle'
            # Kullanıcının ilk yazdığı (tetikleyen) mesajı hafızadan geri çağır
            user_message = session.get('stored_message', user_message)
            # DÖNGÜYÜ KIRAN NOKTA: Tetikleyici kontrolünü atla, direkt AI'ya git
            force_ai_response = True 

    # ------------------------------------------------------------------
    # DURUM 1: NORMAL SOHBET MODU (IDLE)
    # ------------------------------------------------------------------
    # Eğer state 'idle' ise VE form doldurmuyorsak
    if session.get('chat_state') == 'idle':
        
        triggers = ['mesaj', 'message', 'mail', 'iletişim', 'contact', 'ulas', 'ulaş', 'email']
        
        # Tetikleyici kelime var mı? (AMA force_ai_response True ise bakma!)
        is_trigger = any(keyword in user_message.lower() for keyword in triggers)
        
        if is_trigger and not force_ai_response:
            session['stored_message'] = user_message # Mesajı sakla
            session['chat_state'] = 'confirming_contact' # Teyit moduna geç
            
            if lang_code == 'tr': ai_reply = "Bana mesaj bırakmak mı istiyorsunuz? (Evet / Hayır)"
            elif lang_code == 'de': ai_reply = "Möchten Sie eine Nachricht hinterlassen? (Ja / Nein)"
            else: ai_reply = "Do you want to leave a message? (Yes / No)"
            return jsonify({'reply': ai_reply})
        
        else:
            # --- YAPAY ZEKA (HUGGING FACE) ---
            if not HF_API_KEY: return jsonify({'reply': error_message}), 500

            try:
                lang_name = LANGUAGE_NAMES.get(lang_code, 'English')
                vedat_context = current_texts.get("chatbot_context", "")
                
                project_context = "\n**Key Projects:**\n"
                projects_list = PROJECTS.get(lang_code, PROJECTS.get('en', []))
                if projects_list:
                    for proj in projects_list: project_context += f" - {proj['title']}: {proj['desc']}\n"
                else:
                    project_context = "\n(No projects listed.)\n"
                
                system_prompt = f"""
You are a professional portfolio assistant for Vedat Koylahisar.
Answer ONLY based on the facts below. Respond in {lang_name}.

**Facts:**
{vedat_context}
**Projects:**
{project_context}
"""
                headers = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": "meta-llama/Llama-3.1-8B-Instruct",
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}],
                    "max_tokens": 150, "temperature": 0.2
                }
                
                response = requests.post("https://router.huggingface.co/v1/chat/completions", headers=headers, json=payload)
                if response.status_code != 200: return jsonify({'reply': "Model loading..."}), 503

                ai_reply = response.json()['choices'][0]['message']['content'].strip()
                return jsonify({'reply': ai_reply})

            except Exception as e:
                print(f"AI Hata: {e}")
                return jsonify({'reply': error_message}), 500

    # ------------------------------------------------------------------
    # FORM ADIMLARI
    # ------------------------------------------------------------------
    elif current_state == 'waiting_name':
        session['contact_name'] = user_message
        session['chat_state'] = 'waiting_email'
        if lang_code == 'tr': ai_reply = f"Memnun oldum {user_message}. E-posta adresinizi yazar mısınız?"
        elif lang_code == 'de': ai_reply = f"Freut mich, {user_message}. Ihre E-Mail-Adresse bitte?"
        else: ai_reply = f"Nice to meet you {user_message}. Your email address please?"
        return jsonify({'reply': ai_reply})

    elif current_state == 'waiting_email':
        session['contact_email'] = user_message
        session['chat_state'] = 'waiting_message'
        if lang_code == 'tr': ai_reply = "Son olarak mesajınızı yazabilir misiniz?"
        elif lang_code == 'de': ai_reply = "Und schließlich Ihre Nachricht?"
        else: ai_reply = "Finally, your message?"
        return jsonify({'reply': ai_reply})

    elif current_state == 'waiting_message':
        message_body = str(user_message)
        name = str(session.get('contact_name', 'Anonim'))
        email = str(session.get('contact_email', 'Anonim'))
        
        mail_content = f"Chatbot Uzerinden Yeni Mesaj\n\nIsim: {name}\nEmail: {email}\nMesaj:\n{message_body}"
        
        # .env dosyasındaki MAIL_FROM adresine (sana) mail atıyoruz.
        target_email = os.getenv("MAIL_FROM")
        
        print(f"--- Chatbot Mail Denemesi ---\nHedef: {target_email}\nİçerik: {message_body}\n-----------------------------")

        try:
            success = send_mail(to_email=target_email, subject=f"Chatbot: {name}", message_text=mail_content)
            
            if success:
                if lang_code == 'tr': ai_reply = "Mesajınız alındı ve Vedat'a iletildi!"
                elif lang_code == 'de': ai_reply = "Nachricht gesendet!"
                else: ai_reply = "Message forwarded!"
            else:
                raise Exception("send_mail False dondu")
        except Exception as e:
            print(f"KRITIK MAIL HATASI: {e}")
            if lang_code == 'tr': ai_reply = "Mesajınız kaydedildi ancak sistemsel bir hata nedeniyle mail atılamadı."
            else: ai_reply = "Message saved but email failed due to system error."
        
        session['chat_state'] = 'idle'
        session.pop('stored_message', None)
        return jsonify({'reply': ai_reply})

    return jsonify({'reply': "..."})

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


def send_mail(to_email, subject, message_text):
    message = Mail(
        from_email=os.getenv("MAIL_FROM"),
        to_emails=to_email,
        subject=subject,
        plain_text_content=message_text
    )

    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        sg.send(message)
        return True
    except Exception as e:
        print("Mail gonderme hatasi:", e)
        return False



@app.route("/contact", methods=["GET", "POST"])
def contact():
    lang_code = session.get('lang', 'en')
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS.get('en', {}))

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        mail_content = f"""
Yeni Iletisim Formu Mesaji

Isim: {name}
Email: {email}

Mesaj:
{message}
        """

        # Mail gönderme işlemini dene
        success = send_mail(
            to_email=os.getenv("MAIL_FROM"),
            subject="Yeni portfolyo iletisim mesaji",
            message_text=mail_content
        )

        if success:
            # JSON dosyanızdaki "contactSuccess" anahtarını kullanır, yoksa default mesaj döner
            msg = current_texts.get("contactSuccess", "Mesajınız başarıyla gönderildi!")
            flash(msg, "success")
        else:
            # JSON dosyanızdaki "contactError" anahtarını kullanır
            msg = current_texts.get("contactError", "Mesaj gönderilirken bir hata oluştu.")
            flash(msg, "error")

        # ÖNEMLİ: Form gönderildikten sonra aynı sayfaya yönlendiriyoruz (Redirect-After-Post)
        return redirect(url_for('contact'))

    # GET request
    return render_template("contact.html", active='contact')




if __name__ == "__main__":
    app.run(debug=True)