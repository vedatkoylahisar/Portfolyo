/* ==========================================================================
   1. GLOBAL MODAL FONKSÝYONLARI (En Kritik Bölüm)
   Bu fonksiyonlar HTML'den direkt çaðrýldýðý için en dýþta tanýmlanmalý.
   ========================================================================== */

function showModal(message, category) {
    const modal = document.getElementById('flash-modal');
    const msgPara = document.getElementById('modal-message');
    const iconDiv = document.getElementById('modal-icon');

    // Eðer modal sayfada yoksa (baþka sayfadaysak) hata verme, çýk.
    if (!modal || !msgPara || !iconDiv) return;

    // --- KESÝN ÇÖZÜM: MODALI KURTARMA ---
    // Eðer modal bir div'in içine hapsolmuþsa, onu oradan alýp body'nin en altýna taþýyoruz.
    // Bu iþlem, 'transform' veya 'position' çakýþmalarýný %100 çözer.
    document.body.appendChild(modal);
    // ------------------------------------

    // Mesajý ve ikonu ayarla
    msgPara.innerText = message;

    if (category === 'success') {
        iconDiv.innerHTML = '<i class="fas fa-check-circle success-icon"></i>';
    } else {
        iconDiv.innerHTML = '<i class="fas fa-exclamation-circle error-icon"></i>';
    }

    // Kutuyu göster (CSS'deki flex ortalamayý aktif eder)
    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('flash-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Modalýn dýþýndaki siyah alana týklayýnca kapatma
window.addEventListener('click', (event) => {
    const modal = document.getElementById('flash-modal');
    if (event.target === modal) {
        closeModal();
    }
});


/* ==========================================================================
   2. SAYFA YÜKLENÝNCE ÇALIÞACAKLAR (Chatbot, Dil Seçimi vb.)
   ========================================================================== */
document.addEventListener("DOMContentLoaded", () => {

    // --- DÝL SEÇÝCÝ ---
    const langButton = document.getElementById('langButton');
    const langDropdown = document.getElementById('langDropdown');

    if (langButton && langDropdown) {
        langButton.addEventListener('click', (e) => {
            e.stopPropagation();
            langDropdown.classList.toggle('show');
        });
        window.addEventListener('click', () => {
            langDropdown.classList.remove('show');
        });
    }

    // --- YAZI YAZMA (TYPING) ANÝMASYONU ---
    const typingElement = document.querySelector(".typing");
    if (typingElement && typingElement.dataset.texts) {
        try {
            const textArray = JSON.parse(typingElement.dataset.texts);
            if (Array.isArray(textArray) && textArray.length > 0) {
                let textIndex = 0, charIndex = 0, isDeleting = false;

                function typeEffect() {
                    const currentText = textArray[textIndex];

                    if (isDeleting) charIndex--;
                    else charIndex++;

                    typingElement.textContent = currentText.substring(0, charIndex);

                    let typeSpeed = isDeleting ? 75 : 150;

                    if (!isDeleting && charIndex === currentText.length) {
                        isDeleting = true;
                        typeSpeed = 2000; // Yazdýktan sonra bekle
                    } else if (isDeleting && charIndex === 0) {
                        isDeleting = false;
                        textIndex = (textIndex + 1) % textArray.length;
                        typeSpeed = 500; // Sildikten sonra bekle
                    }

                    setTimeout(typeEffect, typeSpeed);
                }
                typeEffect();
            }
        } catch (e) {
            console.error("Typing animation error:", e);
        }
    }

    // --- CHATBOT ÝÞLEVLERÝ ---
    const chatbotForm = document.getElementById('chatbot-form');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotMessages = document.getElementById('chatbot-messages');

    if (chatbotForm) {
        // Yardýmcý fonksiyon: Mesaj ekleme
        function addMessage(sender, text) {
            const messageElement = document.createElement('div');
            messageElement.className = `message ${sender === 'user' ? 'user-message' : 'bot-message'}`;
            messageElement.innerHTML = `<p>${text}</p>`;
            chatbotMessages.appendChild(messageElement);
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
            return messageElement;
        }

        chatbotForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userMessage = chatbotInput.value.trim();
            if (!userMessage) return;

            // Kullanýcý mesajýný göster
            addMessage('user', userMessage);
            chatbotInput.value = "";

            // "Yazýyor..." mesajý
            const loadingMessage = addMessage('bot', '...');

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userMessage })
                });

                if (!response.ok) throw new Error('API Error');

                const data = await response.json();
                // Cevabý güncelle
                loadingMessage.querySelector('p').textContent = data.reply;

            } catch (error) {
                console.error("Chatbot Error:", error);
                loadingMessage.querySelector('p').textContent = "Connection error. Please try again.";
            }
        });
    }
});


/* ==========================================================================
   3. PROFÝL FOTOÐRAFI ANÝMASYONU (Sadece Anasayfa)
   Resimlerin yüklenmesini beklemek için 'load' event'i kullanýlýr.
   ========================================================================== */
window.addEventListener('load', () => {
    const animatedPic = document.getElementById('animated-profile-pic');
    const picPlaceholder = document.getElementById('header-pic-placeholder');
    const chatbotContainer = document.getElementById('chatbot-container');
    const animationWrapper = document.querySelector('.animation-wrapper');

    if (animatedPic && picPlaceholder && animationWrapper) {
        setTimeout(() => {
            const targetRect = picPlaceholder.getBoundingClientRect();
            const wrapperRect = animationWrapper.getBoundingClientRect();

            const finalTop = targetRect.top - wrapperRect.top;
            const finalLeft = targetRect.left - wrapperRect.left;

            animatedPic.classList.add('is-animating');

            // CSS transition ile hareket ettir
            Object.assign(animatedPic.style, {
                width: `${targetRect.width}px`,
                height: `${targetRect.height}px`,
                top: `${finalTop}px`,
                left: `${finalLeft}px`,
                borderWidth: '2px',
                transform: 'translate(0, 0)'
            });

            // Animasyon bitince chatbot'u aç
            setTimeout(() => {
                if (chatbotContainer) chatbotContainer.classList.add('visible');
            }, 2500);

        }, 1000);
    }
});

document.addEventListener('DOMContentLoaded', function () {
    const langToggle = document.getElementById('mobileLangToggle');
    const langDropdown = document.getElementById('mobileLangDropdown');

    if (langToggle && langDropdown) {
        langToggle.addEventListener('click', function (e) {
            // Sadece ekran geniþliði 768px altýndaysa (mobilse) týklamayý iþle
            if (window.innerWidth <= 768) {
                e.preventDefault();
                langDropdown.classList.toggle('show');
            }
        });
    }
});