# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify , flash
from dotenv import load_dotenv
import json
import requests # HTTP istekleri icin
import smtplib
import re
from email.message import EmailMessage
import resend


basedir = os.path.abspath(os.path.dirname(__file__))
os.environ["KAGGLE_CONFIG_DIR"] = basedir

from kaggle.api.kaggle_api_extended import KaggleApi
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

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

with open("chatbot_contact_flow.json", "r", encoding="utf-8") as f:
    CONTACT_FLOW = json.load(f)


def load_data_from_json():
    global MENU_ITEMS, LANGUAGE_NAMES, TRANSLATIONS, PROJECTS, SKILLS
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
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

def send_contact_email(sender_name, sender_email, message_content):
    # Your existing send_mail logic
    success = send_mail(
        to_email=os.getenv("MAIL_FROM"),
        subject=f"New Message from {sender_name}",
        message_text=f"Email: {sender_email}\nMessage: {message_content}"
    )
    return "Success" if success else "Failed"


@app.route("/chat", methods=['POST'])
def chat():
    api_key = os.getenv('CUSTOM_API_KEY')
    api_base = os.getenv('CUSTOM_API_BASE', '').rstrip('/')
    api_url = f"{api_base}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    user_msg = request.json.get('message', '').strip()
    if not user_msg:
        return jsonify({'error': 'No message provided'}), 400

    # 1. Hafizayi (History) Yukle veya Olustur
    if 'chat_history' not in session:
        session['chat_history'] = [
            {"role": "system", "content": "You are Vedat's personal AI assistant. Use 'get_portfolio_data' for info. If the user provides name, email and message, call 'send_contact_email' tool immediately after their confirmation. Do not forget previously shared info."}
        ]
    
    # Kullanicinin yeni mesajini hafizaya ekle
    session['chat_history'].append({"role": "user", "content": user_msg})

    api_url = os.getenv('CUSTOM_API_BASE', '').rstrip('/')
    if not api_url.endswith('/chat/completions'):
        api_url = f"{api_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {os.getenv('CUSTOM_API_KEY')}",
        "Content-Type": "application/json"
    }

    try:
        # STEP 1: Hafizadaki TUM mesajlari gonderiyoruz (Sadece sonuncuyu degil!)
        payload = {
            "model": os.getenv("CUSTOM_MODEL_NAME"),
            "messages": session['chat_history'],
            "tools": tools,
            "tool_choice": "auto"
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=30)
        res_json = response.json()
        response_msg = res_json['choices'][0]['message']

        # STEP 2: Tool Handling
        if response_msg.get("tool_calls"):
            # AI'in tool cagrisini hafizaya ekle
            session['chat_history'].append(response_msg)
            
            for tool_call in response_msg["tool_calls"]:
                func_name = tool_call["function"]["name"]
                args = json.loads(tool_call["function"]["arguments"])
                
                print(f"DEBUG - Executing: {func_name}")
                
                if func_name == "get_portfolio_data":
                    result_content = get_portfolio_data(args.get('data_type'))
                elif func_name == "send_contact_email":
                    # Tool icindeki arguman isimlerine dikkat (name, email, message)
                    result_content = send_contact_email(
                        name=args.get('name') or args.get('sender_name'), 
                        email=args.get('email') or args.get('sender_email'), 
                        message=args.get('message') or args.get('message_content')
                    )
                else:
                    result_content = "Function not found."

                # Tool sonucunu hafizaya ekle
                session['chat_history'].append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": func_name,
                    "content": result_content
                })
            
            # STEP 3: Final Response
            final_payload = {
                "model": os.getenv("CUSTOM_MODEL_NAME"),
                "messages": session['chat_history']
            }
            final_res = requests.post(api_url, json=final_payload, headers=headers, timeout=30)
            final_ans = final_res.json()['choices'][0]['message']
            
            # Final cevabi da hafizaya ekle ve don
            session['chat_history'].append(final_ans)
            session.modified = True # Flask session'i guncelle
            return jsonify({'reply': final_ans['content']})

        # Tool cagrisi yoksa, direkt cevabi hafizaya ekle ve don
        session['chat_history'].append(response_msg)
        session.modified = True
        return jsonify({'reply': response_msg.get('content', '...')})

    except Exception as e:
        print(f"DEBUG - Fatal Error: {str(e)}")
        return jsonify({'reply': "Something went wrong. Let's try again."}), 500


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

    session.pop('chat_history', None)
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


def send_contact_email(name, email, message):
    api_key = os.getenv("RESEND_API_KEY")
    target_email = os.getenv("MAIL_FROM") # Mesajın gideceği kendi mailin
    
    if not api_key:
        print("ERROR: RESEND_API_KEY not found.")
        return "Error: API Key missing."

    resend.api_key = api_key

    try:
        params = {
            "from": "Portfolio Assistant <onboarding@resend.dev>",
            "to": [target_email],
            "subject": f"New Message from {name}",
            "html": f"""
                <h3>New Contact Request</h3>
                <p><strong>Name:</strong> {name}</p>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Message:</strong> {message}</p>
            """
        }

        email_response = resend.Emails.send(params)
        print(f"Resend Success! ID: {email_response}")
        return "Success: Your message has been delivered to Vedat."
    except Exception as e:
        print(f"Resend Error: {str(e)}")
        return f"Error: {str(e)}"



@app.route("/contact", methods=["GET", "POST"])
def contact():
    lang_code = session.get('lang', 'en')
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS.get('en', {}))

    if request.method == "POST":
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
        if "Success" in success_msg:
            msg = current_texts.get("contactSuccess", "Your message has been sent!")
            flash(msg, "success")
        else:
            msg = current_texts.get("contactError", "An error occurred.")
            flash(msg, "error")

        return redirect(url_for('contact'))

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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)