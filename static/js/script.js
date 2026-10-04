/* ==========================================================================
   1. GLOBAL MODAL FONKSİYONLARI (En Kritik Bölüm)
   Bu fonksiyonlar HTML'den direkt çağrıldığı için en dışta tanımlanmalı.
   ========================================================================== */

function showModal(message, category) {
    const modal = document.getElementById('flash-modal');
    const msgPara = document.getElementById('modal-message');
    const iconDiv = document.getElementById('modal-icon');

    // Eğer modal sayfada yoksa (başka sayfadaysak) hata verme, çık.
    if (!modal || !msgPara || !iconDiv) return;

    // --- KESİN ÇÖZÜM: MODALI KURTARMA ---
    // Eğer modal bir div'in içine hapsolmuşsa, onu oradan alıp body'nin en altına taşıyoruz.
    // Bu işlem, 'transform' veya 'position' çakışmalarını %100 çözer.
    document.body.appendChild(modal);
    // ------------------------------------

    // Mesajı ve ikonu ayarla
    msgPara.innerText = message;

    if (category === 'success') {
        iconDiv.innerHTML = '<i class="fas fa-check-circle success-icon"></i>';
    } else {
        iconDiv.innerHTML = '<i class="fas fa-exclamation-circle error-icon"></i>';
    }

    // Kutuyu göster (CSS'deki flex ortalamayı aktif eder)
    modal.style.display = 'flex';
}

function closeModal() {
    const modal = document.getElementById('flash-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Modalın dışındaki siyah alana tıklayınca kapatma
window.addEventListener('click', (event) => {
    const modal = document.getElementById('flash-modal');
    if (event.target === modal) {
        closeModal();
    }
});


/* ==========================================================================
   2. SAYFA YÜKLENİNCE ÇALIŞACAKLAR (Chatbot, Dil Seçimi vb.)
   ========================================================================== */
document.addEventListener("DOMContentLoaded", () => {

    // --- DİL SEÇİCİ ---
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

    // --- YAZI YAZMA (TYPING) ANİMASYONU ---
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
                        typeSpeed = 2000; // Yazdıktan sonra bekle
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

    // --- CHATBOT İŞLEVLERİ ---
    const chatbotForm = document.getElementById('chatbot-form');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotMessages = document.getElementById('chatbot-messages');

    if (chatbotForm) {
        // Sohbet geçmişi tarayıcıda tutulur ve her istekte sunucuya gönderilir
        // (sunucu tarafındaki session cookie'si 4 KB sınırını aşıyordu).
        const chatHistory = [];
        const MAX_HISTORY = 12;
        let isSending = false;

        // Yardımcı fonksiyon: Mesaj ekleme (textContent ile, HTML enjeksiyonuna kapalı)
        function addMessage(sender, text) {
            const messageElement = document.createElement('div');
            messageElement.className = `message ${sender === 'user' ? 'user-message' : 'bot-message'}`;
            const p = document.createElement('p');
            p.style.whiteSpace = 'pre-wrap';
            p.textContent = text;
            messageElement.appendChild(p);
            chatbotMessages.appendChild(messageElement);
            chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
            return messageElement;
        }

        chatbotForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const userMessage = chatbotInput.value.trim();
            if (!userMessage || isSending) return;
            isSending = true;

            // Kullanıcı mesajını göster
            addMessage('user', userMessage);
            chatbotInput.value = "";

            // "Yazıyor..." mesajı
            const loadingMessage = addMessage('bot', '...');

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userMessage, history: chatHistory.slice(-MAX_HISTORY) })
                });

                const data = await response.json().catch(() => ({}));
                if (!response.ok) {
                    const err = new Error('API Error');
                    err.serverReply = data.reply;
                    throw err;
                }

                // Cevabı güncelle
                loadingMessage.querySelector('p').textContent = data.reply;
                chatHistory.push({ role: 'user', content: userMessage });
                chatHistory.push({ role: 'assistant', content: data.reply });

            } catch (error) {
                console.error("Chatbot Error:", error);
                loadingMessage.querySelector('p').textContent =
                    error.serverReply || "Connection error. Please try again.";
            } finally {
                isSending = false;
                chatbotMessages.scrollTop = chatbotMessages.scrollHeight;
            }
        });
    }
});


/* ==========================================================================
   3. PROFİL FOTOĞRAFI ANİMASYONU (Sadece Anasayfa)
   Resimlerin yüklenmesini beklemek için 'load' event'i kullanılır.
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
            // Sadece ekran genişliği 768px altındaysa (mobilse) tıklamayı işle
            if (window.innerWidth <= 768) {
                e.preventDefault();
                langDropdown.classList.toggle('show');
            }
        });
    }
});