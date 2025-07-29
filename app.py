# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session
import json

app = Flask(__name__)
app.secret_key = "supersecretkey" # Session icin gerekli

#======================================================================
# 1. TUM METINLER VE VERILER MERKEZI BIR YERDE
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
        # === PORTFOLYO SAYFASI CEVIRILERI (EN) ===
        "portfolioTitle": "My Latest Projects",
        "portfolioIntro": "Here are a few projects I've worked on recently.",
        "githubButton": "GitHub",
        "demoButton": "Live Demo"
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
        # === PORTFOLYO SAYFASI CEVIRILERI (TR) ===
        "portfolioTitle": "Son Projelerim",
        "portfolioIntro": "Son zamanlarda uzerinde calistigim birkac proje.",
        "githubButton": "GitHub",
        "demoButton": "Canli Demo"
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
        # === PORTFOLYO SAYFASI CEVIRILERI (DE) ===
        "portfolioTitle": "Meine Neuesten Projekte",
        "portfolioIntro": "Hier sind einige Projekte, an denen ich kurzlich gearbeitet habe.",
        "githubButton": "GitHub",
        "demoButton": "Live-Demo"
    }
}

# === YENI: PROJE VERILERI ===
PROJECTS = {
    'tr': [
        {
            'title': "Proje 1 Basligi",
            'desc': "Bu proje, su teknolojiler kullanilarak yapilmis harika bir calismadir.",
            'github': "https://github.com/vedatkoylahisar",
            'demo': "#"
        },
        {
            'title': "Proje 2 Basligi",
            'desc': "Bu da ikinci projemin kisa bir aciklamasi.",
            'github': "https://github.com/vedatkoylahisar",
            'demo': "#"
        },
        {
            'title': "Proje 3 Basligi",
            'desc': "Bu da ucuncu projemin kisa bir aciklamasi.",
            'github': "https://github.com/vedatkoylahisar",
            'demo': "#"
        }
    ],
    'en': [
        {
            'title': "Project 1 Title",
            'desc': "This is a great project made with these technologies.",
            'github': "https://github.com/vedatkoylahisar",
            'demo': "#"
        },
        {
            'title': "Project 2 Title",
            'desc': "A short description for my second project.",
            'github': "https://github.com/vedatkoylahisar",
            'demo': "#"
        },
        {
            'title': "Project 3 Title",
            'desc': "A short description for my third project.",
            'github': "https://github.com/vedatkoylahisar",
            'demo': "#"
        }
    ],
    'de': [
        {
            'title': "Projekttitel 1",
            'desc': "Dies ist ein groSartiges Projekt, das mit diesen Technologien erstellt wurde.",
            'github': "https://github.com/vedatkoylahisar",
            'demo': "#"
        },
        {
            'title': "Projekttitel 2",
            'desc': "Eine kurze Beschreibung fur mein zweites Projekt.",
            'github': "https://github.com/vedatkoylahisar",
            'demo': "#"
        },
        {
            'title': "Projekttitel 3",
            'desc': "Eine kurze Beschreibung fur mein drittes Projekt.",
            'github': "https://github.com/vedatkoylahisar",
            'demo': "#"
        }
    ]
}


#======================================================================
# 2. OTOMATIK DEGISKEN GONDERIMI (CONTEXT PROCESSOR)
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

@app.route("/chat", methods=['POST'])
def chat():
    user_message = request.json.get('message')
    # ... (chatbot logic)
    return {"response": "Anlasilmadi..."}


# --- Sayfa Route'lari ---

@app.route("/")
def home():
    return render_template("index.html", active='home')

@app.route("/about")
def about():
    return render_template("about.html", active='about')

@app.route("/services")
def services():
    return render_template("services.html", active='services')

# === PORTFOLYO ROUTE'U GUNCELLEMESI ===
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
