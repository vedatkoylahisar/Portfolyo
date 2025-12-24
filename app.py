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

# === Hugging Face API Ayarlari ===
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
SKILLS = {}  

with open("chatbot_contact_flow.json", "r", encoding="utf-8") as f:
    CONTACT_FLOW = json.load(f)


def load_data_from_json():
    """data.json dosyasindaki tum verileri global degiskenlere yukler."""
    global MENU_ITEMS, LANGUAGE_NAMES, TRANSLATIONS, PROJECTS, SKILLS
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
   
        MENU_ITEMS = data.get("MENU_ITEMS", [])
        LANGUAGE_NAMES = data.get("LANGUAGE_NAMES", {})
        TRANSLATIONS = data.get("TRANSLATIONS", {})
        PROJECTS = data.get("PROJECTS", {})
        SKILLS = data.get("SKILLS", {})

      
        if not TRANSLATIONS:
            print("UYARI: TRANSLATIONS eksik olabilir.")
        if not PROJECTS:
            print("UYARI: PROJECTS eksik olabilir.")
        if not SKILLS:
            print("UYARI: SKILLS eksik olabilir.")
        
    
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

# ======================================================================
# GUNCEL CHAT ROTASI 
# ======================================================================
@app.route("/chat", methods=['POST'])
def chat():
    # 1. Temel Ayarlar ve Dil
    lang_code = session.get('lang', 'en')
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS.get('en', {}))
    error_message = current_texts.get('chat_general_knowledge_decline', 'Sorry, I cannot help with that.')
    
    user_message = request.json.get('message', '').strip()
    if not user_message:
        return jsonify({'error': 'Mesaj bulunamadi'}), 400

    # 2. Durum Kontrolü (Varsayılan 'idle')
    current_state = session.get('chat_state', 'idle')
    ai_reply = ""
    
    force_ai_response = False 

    # ------------------------------------------------------------------
    # ÖZEL DURUM: TEYİT AŞAMASI (CONFIRMING)
    # ------------------------------------------------------------------
    if current_state == 'confirming_contact':
        affirmative = ['evet', 'yes', 'ja', 'onay', 'istiyorum', 'tabii', 'ok', 'hıhı', 'yep']
        
        msg_lower = user_message.lower()

        if any(word in msg_lower for word in affirmative):
            session['chat_state'] = 'waiting_name'
            if lang_code == 'tr': ai_reply = "Harika. Öncelikle adınızı öğrenebilir miyim?"
            elif lang_code == 'de': ai_reply = "Super. Darf ich zuerst Ihren Namen erfahren?"
            else: ai_reply = "Great. May I have your name first?"
            return jsonify({'reply': ai_reply})
        
        else:
            session['chat_state'] = 'idle'
            user_message = session.get('stored_message', user_message)
            force_ai_response = True 
            current_state = 'idle' 

    # ------------------------------------------------------------------
    # DURUM 1: NORMAL SOHBET MODU (IDLE)
    # ------------------------------------------------------------------
    if current_state == 'idle':
        
        triggers = ['mesaj', 'message', 'mail', 'iletişim', 'contact', 'ulas', 'ulaş', 'email']
        is_trigger = any(keyword in user_message.lower() for keyword in triggers)
        
        if is_trigger and not force_ai_response:
            session['stored_message'] = user_message
            session['chat_state'] = 'confirming_contact'
            
            if lang_code == 'tr': ai_reply = "Bana mesaj bırakmak mı istiyorsunuz? (Evet / Hayır)"
            elif lang_code == 'de': ai_reply = "Möchten Sie eine Nachricht hinterlassen? (Ja / Nein)"
            else: ai_reply = "Do you want to leave a message? (Yes / No)"
            return jsonify({'reply': ai_reply})
        
        else:
            # --- YAPAY ZEKA (HUGGING FACE) ---
            # 1. API KEY KONTROLÜ 
            if not HF_API_KEY: 
                print("HATA: HUGGINGFACE_API_KEY sunucuda bulunamadi!")
                return jsonify({'reply': error_message}), 500

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
                
                if response.status_code != 200: 
                    print(f"HF API Hatasi: {response.status_code} - {response.text}")
                    return jsonify({'reply': "Model loading..."}), 503

                ai_reply = response.json()['choices'][0]['message']['content'].strip()
                return jsonify({'reply': ai_reply})

            except Exception as e:
                print(f"AI Kod Hatasi: {e}")
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
        target_email = os.getenv("MAIL_FROM")
        
        try:
            success = send_mail(to_email=target_email, subject=f"Chatbot: {name}", message_text=mail_content)
            if success:
                if lang_code == 'tr': ai_reply = "Mesajınız alındı ve Vedat'a iletildi!"
                elif lang_code == 'de': ai_reply = "Nachricht gesendet!"
                else: ai_reply = "Message forwarded!"
            else:
                raise Exception("send_mail False dondu")
        except Exception as e:
            print(f"MAIL HATASI: {e}")
            if lang_code == 'tr': ai_reply = "Mesajınız kaydedildi ancak sistemsel bir hata nedeniyle mail atılamadı."
            else: ai_reply = "Message saved but email failed due to system error."
        
        session['chat_state'] = 'idle'
        session.pop('stored_message', None)
        return jsonify({'reply': ai_reply})

    # HİÇBİR ŞARTA UYMAZSA (DEBUG İÇİN)
    return jsonify({'reply': "..."})

def fetch_kaggle_projects():
    try:
        api = KaggleApi()
        api.authenticate()

        username = os.getenv("KAGGLE_USERNAME") or "vedatkoylahisar"

        # 100 projeye kadar çek, tarihe göre sırala
        kernels = api.kernels_list(user=username, page_size=100, sort_by='dateRun')
        kernels = list(kernels) 

        projects = []
        for k in kernels:
            if getattr(k, 'isPrivate', False):
                continue 

            # Açıklama kontrolü
            desc = getattr(k, 'description', None) 
            
            projects.append({
                "title": getattr(k, 'title', 'Untitled'),
                "description": desc,
                "url": f"https://www.kaggle.com/code/{username}/{k.ref.split('/')[-1]}",
                "image": "/static/images/kaggle_logo.png"
            })
        return projects
    except Exception as e:
        print("Kaggle API error:", e)
        return []


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




@app.route("/services")
def services():
    return render_template("services.html", active='services')

@app.route("/portfolio")
def portfolio():
    lang_code = session.get('lang', 'en')
    
    # 1. O dile ait genel çevirileri çek (Menü, başlıklar vb. için)
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS["en"])

    # 2. Yerel projeleri (JSON içindeki 'projects' listesinden) al
    # DİKKAT: Artık PROJECTS global değişkeninden değil, current_texts içinden alıyoruz
    projects_from_json = current_texts.get("projects", [])
    
    # 3. Kaggle ve LeetCode verilerini çek
    kaggle_list = fetch_kaggle_projects()
    leetcode_solutions = fetch_leetcode_solutions()
    
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
        projects=all_projects,     # Birleştirilmiş liste
        leetcode=leetcode_solutions
    )


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


def fetch_leetcode_solutions():
    # GitHub API URL'si
    github_user = "vedatkoylahisar"
    repo_name = "leetcode-problems"
    url = f"https://api.github.com/repos/{github_user}/{repo_name}/contents"

    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            files = response.json()
            solutions = []
            
            for file in files:
                if file['name'].endswith(('.py', '.cpp', '.java', '.js')) and file['type'] == 'file':
                    
                   
                    clean_name = file['name'].rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                    
                    solutions.append({
                        'title': clean_name,       # Ekranda görünecek isim
                        'filename': file['name'],  # Orijinal dosya ismi
                        'url': file['html_url'],   # GitHub'daki kodun linki
                        'language': file['name'].split('.')[-1] # py, cpp vs.
                    })
            return solutions
        else:
            print(f"GitHub Hatası: {response.status_code}")
            return []
            
    except Exception as e:
        print("GitHub Bağlantı Hatası:", e)
        return []



if __name__ == "__main__":
    app.run(debug=True)