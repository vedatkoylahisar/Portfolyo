# -*- coding: utf-8 -*-
import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from dotenv import load_dotenv
import json
import requests # Google API yerine HTTP istekleri icin bunu kullaniyoruz

# .env dosyasindaki degiskenleri yukle
load_dotenv()

app = Flask(__name__)
app.secret_key = "supersecretkey"

# === Hugging Face API Ayarlarý ===
HF_MODEL_ID = "meta-llama/Llama-3.1-8B-Instruct"  # veya digerlerinden biri
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL_ID}"
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")


if not HF_API_KEY:
    print("="*50)
    print("HATA: HUGGINGFACE_API_KEY bulunamadi.")
    print("Lutfen .env dosyasini kontrol edin.")
    print("="*50)

#======================================================================
# 1. TUM METINLER VE VERILER (Degisiklik Yok)
#======================================================================
MENU_ITEMS = [
    {'name_key': 'home', 'endpoint': 'home'},
    {'name_key': 'about', 'endpoint': 'about'},
    {'name_key': 'services', 'endpoint': 'services'},
    {'name_key': 'portfolio', 'endpoint': 'portfolio'},
    {'name_key': 'contact', 'endpoint': 'contact'}
]

LANGUAGE_NAMES = {
    'en': 'English',
    'tr': 'Turkce',
    'de': 'Deutsch'
}

TRANSLATIONS = {
    'en': {
        "home": "Home", "about": "About", "services": "Services", "portfolio": "Portfolio", "contact": "Contact",
        "greeting": "Hello, It's Me", "name": "Vedat Koylahisar", "profession": "And I'm a", "description": "I am a software developer.", "downloadCV": "Download CV",
        "typingText": ["AI Developer", "Data Analyst", "Freelancer"],
        "aboutTitle": "About Me",
        "aboutContent": ["..."],
        "comingSoonMessage": "This section will be available very soon...",
        "contactIntro": "Have a project in mind or just want to say hello? Feel free to reach out...",
        "contactFormTitle": "Send a Message", "formName": "Your Name", "formEmail": "Your Email", "formMessage": "Your Message", "formSend": "Send Message",
        "or": "OR", "contactSocialTitle": "Connect with Me",
        "chatbotTitle": "AI Assistant", "chatbotContactIntro": "Alternatively, you can leave a message with me...", "chatbotPlaceholder": "Type a message...",
        "portfolioTitle": "My Latest Projects",
        "portfolioIntro": "Here are a few projects I've worked on recently.",
        "githubButton": "GitHub",
        "demoButton": "Demo",
        "chatbotHello": "Hello! I am Vedat's digital assistant. How can I help you?",
        "chat_answer_about": "Vedat is a software developer. You can learn more on the 'About' page.",
        "chat_answer_contact": "You can reach Vedat via the contact form on the 'Contact' page or through his social media links.",
        "chat_answer_projects": "You can see Vedat's latest work on the 'Portfolio' page.",
        "chat_answer_default": "I'm sorry, I didn't quite understand that. I can help with questions about Vedat, his projects, or how to contact him."
    },
    'tr': {
        "home": "Anasayfa", "about": "Hakkimda", "services": "Hizmetler", "portfolio": "Portfolyo", "contact": "Iletisim",
        "greeting": "Merhaba, Ben", "name": "Vedat Koylahisar", "profession": "Ve Ben bir", "description": "Ben yazilim gelistiricisiyim.", "downloadCV": "CV Indir",
        "typingText": ["Yapay Zeka Gelistiricisi", "Veri Analisti", "Freelancer"],
        "aboutTitle": "Hakkimda",
        "aboutContent": ["..."],
        "comingSoonMessage": "Bu bolum cok yakinda sizlerle olacak...",
        "contactIntro": "Aklinizda bir proje mi var veya sadece merhaba mi demek istiyorsunuz? Bana ulasmaktan cekinmeyin...",
        "contactFormTitle": "Mesaj Gonderin", "formName": "Adiniz", "formEmail": "E-posta Adresiniz", "formMessage": "Mesajiniz", "formSend": "Mesaji Gonder",
        "or": "VEYA", "contactSocialTitle": "Sosyal Medyada Ulasin",
        "chatbotTitle": "Yapay Zeka Asistani", "chatbotContactIntro": "Alternatif olarak, mesajinizi bana birakabilirsiniz...", "chatbotPlaceholder": "Bir mesaj yazin...",
        "portfolioTitle": "Son Projelerim",
        "portfolioIntro": "Son zamanlarda uzerinde calistigim birkac proje.",
        "githubButton": "GitHub",
        "demoButton": "Demo",
        "chatbotHello": "Merhaba! Ben Vedat'in dijital asistaniyim. Nasil yardimci olabilirim?",
        "chat_answer_about": "Vedat bir yazilim gelistiricisidir. 'Hakkimda' sayfasindan daha fazla bilgi edinebilirsiniz.",
        "chat_answer_contact": "Vedat'a 'Iletisim' sayfasindaki form uzerinden veya sosyal medya linklerinden ulasabilirsiniz.",
        "chat_answer_projects": "Vedat'in son calismalarini 'Portfolyo' sayfasinda gorebilirsiniz.",
        "chat_answer_default": "Uzgunum, tam anlayamadim. Vedat, projeleri veya iletisim yollari hakkindaki sorularda yardimci olabilirim."
    },
    'de': {
        "home": "Startseite", "about": "Uber Mich", "services": "Dienstleistungen", "portfolio": "Portfolio", "contact": "Kontakt",
        "greeting": "Hallo, Ich bin", "name": "Vedat Koylahisar", "profession": "Und ich bin ein", "description": "Ich bin Softwareentwickler.", "downloadCV": "Lebenslauf herunterladen",
        "typingText": ["KI-Entwickler", "Datenanalyst", "Freiberufler"],
        "aboutTitle": "Uber Mich",
        "aboutContent": ["..."],
        "comingSoonMessage": "Dieser Bereich wird in Kurze verfugbar sein...",
        "contactIntro": "Haben Sie ein Projekt im Sinn oder mochten Sie einfach nur Hallo sagen? Zogern Sie nicht, mich zu kontaktieren...",
        "contactFormTitle": "Nachricht Senden", "formName": "Ihr Name", "formEmail": "Ihre E-Mail", "formMessage": "Ihre Nachricht", "formSend": "Nachricht Senden",
        "or": "ODER", "contactSocialTitle": "Verbinden Sie sich mit mir",
        "chatbotTitle": "KI-Assistent", "chatbotContactIntro": "Alternativ konnen Sie mir eine Nachricht hinterlassen...", "chatbotPlaceholder": "Nachricht eingeben...",
        "portfolioTitle": "Meine Neuesten Projekte",
        "portfolioIntro": "Hier sind einige Projekte, an denen ich kurzlich gearbeitet habe.",
        "githubButton": "GitHub",
        "demoButton": "Demo",
        "chatbotHello": "Hallo! Ich bin Vedats digitaler Assistent. Wie kann ich Ihnen helfen?",
        "chat_answer_about": "Vedat ist ein Softwareentwickler. Mehr uber ihn erfahren Sie auf der 'Uber Mich'-Seite.",
        "chat_answer_contact": "Sie konnen Vedat uber das Kontaktformular auf der 'Kontakt'-Seite oder seine Social-Media-Links erreichen.",
        "chat_answer_projects": "Vedats neueste Arbeiten finden Sie auf der 'Portfolio'-Seite.",
        "chat_answer_default": "Entschuldigung, das habe ich nicht ganz verstanden. Ich kann bei Fragen zu Vedat, seinen Projekten oder zur Kontaktaufname helfen."
    }
}

PROJECTS = {
    # ... (Proje verilerin degismeden oldugu gibi kaliyor) ...
}

#======================================================================
# 2. CONTEXT PROCESSOR (Degisiklik Yok)
#======================================================================

@app.context_processor
def inject_global_vars():
    lang_code = session.get('lang', 'en')
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS['en'])
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
    if 'lang' not in session:
        session['lang'] = 'en'

@app.route("/set_language/<lang_code>")
def set_language(lang_code):
    if lang_code in LANGUAGE_NAMES:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('home'))

@app.route("/chat", methods=['POST'])
def chat():
    lang_code = session.get('lang', 'en')
    error_message = TRANSLATIONS.get(lang_code, TRANSLATIONS['en']).get('chat_answer_default')

    if not HF_API_KEY:
        print("Hugging Face API Anahtari eksik.")
        return jsonify({'reply': error_message}), 500

    try:
        user_message = request.json.get('message')
        lang_name = LANGUAGE_NAMES.get(lang_code, 'English')

        if not user_message:
            return jsonify({'error': 'Mesaj bulunamadi'}), 400

        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "meta-llama/Llama-3.1-8B-Instruct",
            "messages": [
                {"role": "system", "content": f"You are Vedat Koylahisar's portfolio assistant. Respond in {lang_name} only."},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }

        response = requests.post("https://router.huggingface.co/v1/chat/completions",
                                 headers=headers, json=payload)

        if response.status_code != 200:
            print(f"Hugging Face API Hatasi: {response.status_code} - {response.text}")
            raise Exception("API request failed")

        data = response.json()
        ai_reply = data['choices'][0]['message']['content'].strip()

        return jsonify({'reply': ai_reply})

    except Exception as e:
        print(f"Chatbot Hata: {e}")
        return jsonify({'reply': error_message}), 500


# --- Sayfa Route'lari (Degisiklik Yok) ---

@app.route("/")
def home():
    return render_template("index.html", active='home')

@app.route("/about")
def about():
    return render_template("about.html", active='about')

@app.route("/services")
def services():
    return render_template("services.html", active='services')

@app.route("/portfolio")
def portfolio():
    lang_code = session.get('lang', 'en')
    projects_list = PROJECTS.get(lang_code, PROJECTS['en'])
    return render_template("portfolio.html", active='portfolio', projects=projects_list)

@app.route("/contact")
def contact():
    return render_template("contact.html", active='contact')


if __name__ == "__main__":
    app.run(debug=True)