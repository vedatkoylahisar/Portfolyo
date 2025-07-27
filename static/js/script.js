// Language translations without special characters
const translations = {
    en: {
        home: "Home",
        about: "About",
        services: "Services",
        portfolio: "Portfolio",
        contact: "Contact",
        greeting: "Hello, It's Me",
        name: "Vedat Koylahisar",
        profession: "And I'm a",
        description: "I am a software developer.",
        downloadCV: "Download CV",
        typingText: ["AI Developer", "Data Analyst", "Freelancer"],
        languageName: "English"
    },
    tr: {
        home: "Anasayfa",
        about: "Hakkinda",
        services: "Hizmetler",
        portfolio: "Portfolyo",
        contact: "Iletisim",
        greeting: "Merhaba, Ben",
        name: "Vedat Koylahisar",
        profession: "Ve Ben bir",
        description: "Ben yazilim gelistiricisiyim.",
        downloadCV: "CV Indir",
        typingText: ["Yapay Zeka Gelistiricisi", "Veri Analisti", "Freelancer"],
        languageName: "Turkce"
    },
    de: {
        home: "Startseite",
        about: "Uber",
        services: "Dienstleistungen",
        portfolio: "Portfolio",
        contact: "Kontakt",
        greeting: "Hallo, Ich bin",
        name: "Vedat Koylahisar",
        profession: "Und ich bin ein",
        description: "Ich bin Softwareentwickler.",
        downloadCV: "Lebenslauf herunterladen",
        typingText: ["KI-Entwickler", "Datenanalyst", "Freiberufler"],
        languageName: "Deutsch"
    }
};

// Global variables
let textArray = [];
let typingElement;
let textIndex = 0;
let charIndex = 0;
let isDeleting = false;

// Typing animation
function typeEffect() {
    if (!textArray.length || !typingElement) return;

    const currentText = textArray[textIndex];
    if (isDeleting) {
        typingElement.textContent = currentText.substring(0, charIndex - 1);
        charIndex--;
    } else {
        typingElement.textContent = currentText.substring(0, charIndex + 1);
        charIndex++;
    }

    if (!isDeleting && charIndex === currentText.length) {
        isDeleting = true;
        setTimeout(typeEffect, 1000);
    } else if (isDeleting && charIndex === 0) {
        isDeleting = false;
        textIndex = (textIndex + 1) % textArray.length;
        setTimeout(typeEffect, 200);
    } else {
        setTimeout(typeEffect, isDeleting ? 50 : 150);
    }
}

// Set language and update content
function setLanguage(language) {
    const t = translations[language];

    document.querySelector('nav ul li:nth-child(1) a').textContent = t.home;
    document.querySelector('nav ul li:nth-child(2) a').textContent = t.about;
    document.querySelector('nav ul li:nth-child(3) a').textContent = t.services;
    document.querySelector('nav ul li:nth-child(4) a').textContent = t.portfolio;
    document.querySelector('nav ul li:nth-child(5) a').textContent = t.contact;
    document.querySelector('.hero-text h3').innerHTML = t.greeting;
    document.querySelector('.hero-text h1').textContent = t.name;
    document.querySelector('.hero-text h3 span').textContent = t.profession;
    document.querySelector('.hero-text p').textContent = t.description;
    document.querySelector('.btn').textContent = t.downloadCV;
    document.getElementById('langButton').textContent = t.languageName;

    // Update typing text array and reset indexes
    textArray = t.typingText;
    textIndex = 0;
    charIndex = 0;
    isDeleting = false;
}

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", () => {
    typingElement = document.querySelector(".typing");

    // Flask tarafýndan template içinde gönderilen lang deðiþkenini kullan
    const currentLang = document.documentElement.lang || 'en';
    setLanguage(currentLang);
    typeEffect();

    const langButton = document.getElementById('langButton');
    const langDropdown = document.getElementById('langDropdown');

    langButton.addEventListener('click', () => {
        langDropdown.classList.toggle('show');
    });

    // Dil deðiþtirme dropdown linklerine backend yönlendirmesi ekle
    const langLinks = langDropdown.querySelectorAll('a');
    langLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            // normal link davranýþý backend'de session dil deðiþtiriyor ve sayfayý yeniliyor
        });
    });

    window.addEventListener('click', (event) => {
        if (!event.target.matches('.lang-button')) {
            if (langDropdown.classList.contains('show')) {
                langDropdown.classList.remove('show');
            }
        }
    });
});
