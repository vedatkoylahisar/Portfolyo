# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session
# 'json' importuna artik ihtiyacimiz yok, cunku Flask'in yerlesik filtresini kullanacagiz.

app = Flask(__name__)
app.secret_key = "supersecretkey" # Session icin gerekli

#======================================================================
# 1. TUM METINLER VE VERILER MERKEZI BIR YERDE (Degisiklik yok)
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
        ]
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
        ]
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
        ]
    }
}


#======================================================================
# 2. OTOMATIK DEGISKEN GONDERIMI (CONTEXT PROCESSOR)
#======================================================================

@app.context_processor
def inject_global_vars():
    """Bu fonksiyon, tum templatelere otomatik olarak degisken gonderir."""
    lang_code = session.get('lang', 'en')
    current_texts = TRANSLATIONS.get(lang_code, TRANSLATIONS['en'])
    
    # === ISTE DUZELTME BURADA! ===
    # Ozel 'to_json' fonksiyonunu ve importunu kaldirdik.
    # Cunku Flask'in kendi yerlesik '|tojson' filtresi bu isi zaten yapiyor.
    # Bu sayede kodumuz daha temiz ve Flask standartlarina daha uygun oldu.
    
    return dict(
        menu=MENU_ITEMS,
        lang=lang_code,
        texts=current_texts,
        language_names=LANGUAGE_NAMES
    )


#======================================================================
# 3. DIL YONETIMI VE SAYFA ROUTE'LARI (Degisiklik yok)
#======================================================================

@app.before_request
def ensure_lang_in_session():
    """Her istekten once session'da dil oldugundan emin olur."""
    if 'lang' not in session:
        session['lang'] = 'en'  # Varsayilan dil

@app.route("/set_language/<lang_code>")
def set_language(lang_code):
    """Session'daki dili degistirir ve geldigi sayfaya geri doner."""
    if lang_code in LANGUAGE_NAMES:
        session['lang'] = lang_code
    return redirect(request.referrer or url_for('home'))


# --- Sayfa Route'lari (Artik cok daha temiz!) ---

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
