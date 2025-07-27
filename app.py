# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Session için gerekli

menu_items = [
    {'name': 'Home', 'endpoint': 'home'},
    {'name': 'About', 'endpoint': 'about'},
    {'name': 'Services', 'endpoint': 'services'},
    {'name': 'Portfolio', 'endpoint': 'portfolio'},
    {'name': 'Contact', 'endpoint': 'contact'}
]

# Dil isimleri (backend'den template'e geçilecek)
language_names = {
    'en': 'English',
    'tr': 'Turkce',
    'de': 'Deutsch'
}

@app.before_request
def ensure_lang_in_session():
    if 'lang' not in session:
        session['lang'] = 'en'  # Varsayýlan dil

@app.route("/set_language/<lang>")
def set_language(lang):
    if lang in ['en', 'tr', 'de']:
        session['lang'] = lang
    # Geldiði sayfaya döner, yoksa anasayfa
    return redirect(request.referrer or url_for('home'))

@app.route("/")
def home():
    lang = session.get('lang', 'en')
    return render_template("index.html", menu=menu_items, active='home', lang=lang, language_names=language_names)

@app.route("/about")
def about():
    lang = session.get('lang', 'en')
    return render_template("about.html", menu=menu_items, active='about', lang=lang, language_names=language_names)

@app.route("/services")
def services():
    lang = session.get('lang', 'en')
    return render_template("services.html", menu=menu_items, active='services', lang=lang, language_names=language_names)

@app.route("/portfolio")
def portfolio():
    lang = session.get('lang', 'en')
    return render_template("portfolio.html", menu=menu_items, active='portfolio', lang=lang, language_names=language_names)

@app.route("/contact")
def contact():
    lang = session.get('lang', 'en')
    return render_template("contact.html", menu=menu_items, active='contact', lang=lang, language_names=language_names)

if __name__ == "__main__":
    app.run(debug=True)
