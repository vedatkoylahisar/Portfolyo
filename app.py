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
        "aboutContent": [
            "Hello! I am Vedat Koylahisar, a 4th year Computer Engineering student at Kocaeli University.",
            "I have been actively interested in software development for about four years, working on projects for desktop, web, and mobile platforms.",
            "I develop applications in C#, Python, and Java, aiming to advance in database structures, artificial intelligence, and data science.",
            "Thanks to internships at Bimser and Keep Games, I gained practical experience with low-code platforms and game engines.",
            "In my free time, I travel to explore different cultures and share stories about software and entrepreneurship on TikTok and Reels."
        ],
        "comingSoonMessage": "This section will be available very soon...",
        # === ILETISIM SAYFASI CEVIRILERI (EN) ===
        "contactIntro": "Have a project in mind or just want to say hello? Feel free to reach out. I'm always open to discussing new projects and creative ideas.",
        "contactFormTitle": "Send a Message",
        "formName": "Your Name",
        "formEmail": "Your Email",
        "formMessage": "Your Message",
        "formSend": "Send Message",
        "or": "OR",
        "contactSocialTitle": "Connect with Me",
        "chatbotTitle": "AI Assistant",
        "chatbotContactIntro": "Alternatively, you can leave a message with me, and I'll make sure Vedat gets it!",
        "chatbotPlaceholder": "Type a message..."
    },
    'tr': {
        "home": "Anasayfa", "about": "Hakkimda", "services": "Hizmetler", "portfolio": "Portfolyo", "contact": "Iletisim",
        "greeting": "Merhaba, Ben", "name": "Vedat Koylahisar", "profession": "Ve Ben bir", "description": "Ben yazilim gelistiricisiyim.", "downloadCV": "CV Indir",
        "typingText": ["Yapay Zeka Gelistiricisi", "Veri Analisti", "Freelancer"],
        "aboutTitle": "Hakkimda",
        "aboutContent": [
            "Merhaba! Ben Vedat Koylahisar, Kocaeli Universitesi Bilgisayar Muhendisligi 4. sinif ogrencisiyim.",
            "Yaklasik dort yildir aktif olarak yazilim gelistirme ile ilgileniyor; masaustu, web ve mobil platformlar icin projeler yapiyorum.",
            "C#, Python, Java gibi dillerde uygulama gelistiriyor; veritabani yapilari, yapay zeka ve veri bilimi alanlarinda ilerlemeyi hedefliyorum.",
            "Bimser ve Keep Games firmalarinda yaptigim stajlar sayesinde dusuk kod platformlari ve oyun motorlari konusunda uygulamali tecrube kazandim.",
            "Bos zamanlarimda farkli kulturleri kesfetmek icin seyahat ediyor; TikTok ve Reels platformlarinda yazilim ve girisimcilik hikayeleri paylasiyorum."
        ],
        "comingSoonMessage": "Bu bolum cok yakinda sizlerle olacak...",
        # === ILETISIM SAYFASI CEVIRILERI (TR) ===
        "contactIntro": "Aklinizda bir proje mi var veya sadece merhaba mi demek istiyorsunuz? Bana ulasmaktan cekinmeyin. Yeni projeleri ve yaratici fikirleri tartismaya her zaman acigim.",
        "contactFormTitle": "Mesaj Gonderin",
        "formName": "Adiniz",
        "formEmail": "E-posta Adresiniz",
        "formMessage": "Mesajiniz",
        "formSend": "Mesaji Gonder",
        "or": "VEYA",
        "contactSocialTitle": "Sosyal Medyada Ulasin",
        "chatbotTitle": "Yapay Zeka Asistani",
        "chatbotContactIntro": "Alternatif olarak, mesajinizi bana birakabilirsiniz, Vedat'a ulastigindan emin olurum!",
        "chatbotPlaceholder": "Bir mesaj yazin..."
    },
    'de': {
        "home": "Startseite", "about": "Uber Mich", "services": "Dienstleistungen", "portfolio": "Portfolio", "contact": "Kontakt",
        "greeting": "Hallo, Ich bin", "name": "Vedat Koylahisar", "profession": "Und ich bin ein", "description": "Ich bin Softwareentwickler.", "downloadCV": "Lebenslauf herunterladen",
        "typingText": ["KI-Entwickler", "Datenanalyst", "Freiberufler"],
        "aboutTitle": "Uber Mich",
        "aboutContent": [
            "Hallo! Ich bin Vedat Koylahisar, ein Student der Informatik im 4. Jahr an der Universitat Kocaeli.",
            "Seit etwa vier Jahren beschaftige ich mich aktiv mit Softwareentwicklung und arbeite an Projekten fur Desktop-, Web- und Mobilplattformen.",
            "Ich entwickle Anwendungen in C#, Python und Java und strebe Fortschritte in Datenbankstrukturen, kunstlicher Intelligenz und Datenwissenschaft an.",
            "Durch Praktika bei Bimser und Keep Games habe ich praktische Erfahrungen mit Low-Code-Plattformen und Spiel-Engines gesammelt.",
            "In meiner Freizeit reise ich gerne, um verschiedene Kulturen zu entdecken, und teile Geschichten uber Software und Unternehmertum auf TikTok und Reels."
        ],
        "comingSoonMessage": "Dieser Bereich wird in Kurze verfugbar sein...",
        # === ILETISIM SAYFASI CEVIRILERI (DE) ===
        "contactIntro": "Haben Sie ein Projekt im Sinn oder mochten Sie einfach nur Hallo sagen? Zogern Sie nicht, mich zu kontaktieren. Ich bin immer offen fur die Diskussion neuer Projekte und kreativer Ideen.",
        "contactFormTitle": "Nachricht Senden",
        "formName": "Ihr Name",
        "formEmail": "Ihre E-Mail",
        "formMessage": "Ihre Nachricht",
        "formSend": "Nachricht Senden",
        "or": "ODER",
        "contactSocialTitle": "Verbinden Sie sich mit mir",
        "chatbotTitle": "KI-Assistent",
        "chatbotContactIntro": "Alternativ konnen Sie mir eine Nachricht hinterlassen, und ich werde sicherstellen, dass Vedat sie erhalt!",
        "chatbotPlaceholder": "Nachricht eingeben..."
    }
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

# Chatbot icin route
@app.route("/chat", methods=['POST'])
def chat():
    user_message = request.json.get('message')
    if "merhaba" in user_message.lower():
        bot_response = "Merhaba! Nasil yardimci olabilirim?"
    elif "hakkinda" in user_message.lower() or "kimsin" in user_message.lower():
        bot_response = "Ben Vedat'in portfolyo sitesi icin olusturdugu bir sohbet asistaniyim."
    elif "yetenek" in user_message.lower() or "ne yapar" in user_message.lower():
        bot_response = "Vedat; Python, Flask, C# ve Veri Bilimi konularinda calismalar yapiyor. Daha fazla bilgi icin portfolyosunu inceleyebilirsiniz."
    else:
        bot_response = "Anlayamadim, lutfen farkli bir sey sorun. Ornegin: 'Yeteneklerin nelerdir?'"
    return {"response": bot_response}


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

@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html", active='portfolio')

@app.route("/contact")
def contact():
    return render_template("contact.html", active='contact')


if __name__ == "__main__":
    app.run(debug=True)
