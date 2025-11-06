//================================================
// FOTOGRAF ANIMASYONUNU YONETEN KOD
//================================================

// 'window.onload', tum sayfa (resimler, stiller vb.) yuklendikten sonra calisir.
window.onload = () => {
    const animatedPic = document.getElementById('animated-profile-pic');
    const picPlaceholder = document.getElementById('header-pic-placeholder');
    const chatbotContainer = document.getElementById('chatbot-container');
    const animationWrapper = document.querySelector('.animation-wrapper'); // Fotografin icinde bulundugu kutu

    // Bu animasyon sadece anasayfada calisacagi icin,
    // ilgili elementlerin varligini kontrol ediyoruz.
    if (animatedPic && picPlaceholder && animationWrapper) {

        // Sayfa yuklendikten 1 saniye sonra animasyonu baslat.
        setTimeout(() => {
            // 1. Hedefin (placeholder) ve ana kutunun (wrapper) konumlarini al
            const targetRect = picPlaceholder.getBoundingClientRect();
            const wrapperRect = animationWrapper.getBoundingClientRect();

            // === ISTE DUZELTME BURADA! ===
            // Hedefin konumunu, icinde bulundugu kutuya gore hesapliyoruz.
            // Bu, fotografin tam olarak dogru noktaya gitmesini saglar.
            const finalTop = targetRect.top - wrapperRect.top;
            const finalLeft = targetRect.left - wrapperRect.left;

            // 2. Mavi parlamanin kaybolmasi icin ozel class'i ekle
            animatedPic.classList.add('is-animating');

            // 3. Animasyonlu fotografa yeni ve dogru stilleri uygula.
            animatedPic.style.width = `${targetRect.width}px`;
            animatedPic.style.height = `${targetRect.height}px`;
            animatedPic.style.top = `${finalTop}px`;
            animatedPic.style.left = `${finalLeft}px`;
            animatedPic.style.borderWidth = '2px';
            animatedPic.style.transform = 'translate(0, 0)'; // Merkezleme transform'unu sifirla

            // 4. Fotografin animasyonu biterken (2.5s sonra) chatbot'u goster
            setTimeout(() => {
                if (chatbotContainer) {
                    chatbotContainer.classList.add('visible');
                }
            }, 2500);

        }, 1000); // 1 saniye sonra baslat
    }
};


//================================================
// DIGER SAYFA ISLEVLERI
//================================================
document.addEventListener("DOMContentLoaded", () => {

    //---------------------------------
    // DIL SECICI DROPDOWN MENUSU
    // (Kodun degismedi)
    //---------------------------------
    const langButton = document.getElementById('langButton');
    const langDropdown = document.getElementById('langDropdown');
    if (langButton && langDropdown) {
        langButton.addEventListener('click', (event) => {
            event.stopPropagation();
            langDropdown.classList.toggle('show');
        });
        window.addEventListener('click', () => {
            if (langDropdown.classList.contains('show')) {
                langDropdown.classList.remove('show');
            }
        });
    }

    //---------------------------------
    // YAZI YAZMA ANIMASYONU
    // (Kodun degismedi, sadece Turkce karakterler kaldirildi)
    //---------------------------------
    const typingElement = document.querySelector(".typing");
    if (typingElement) {
        const dataTexts = typingElement.dataset.texts;
        if (dataTexts) {
            try {
                const textArray = JSON.parse(dataTexts);
                if (Array.isArray(textArray) && textArray.length > 0) {
                    let textIndex = 0, charIndex = 0, isDeleting = false;
                    function typeEffect() {
                        const currentText = textArray[textIndex];
                        if (isDeleting) {
                            charIndex--;
                        } else {
                            charIndex++;
                        }
                        typingElement.textContent = currentText.substring(0, charIndex);

                        if (!isDeleting && charIndex === currentText.length) {
                            isDeleting = true;
                            setTimeout(() => { typeEffect(); }, 2000);
                        } else if (isDeleting && charIndex === 0) {
                            isDeleting = false;
                            textIndex = (textIndex + 1) % textArray.length;
                            setTimeout(() => { typeEffect(); }, 500);
                        } else {
                            setTimeout(() => { typeEffect(); }, isDeleting ? 75 : 150);
                        }
                    }
                    typeEffect();
                }
            } catch (e) {
                console.error("Hata: 'data-texts' verisi JSON formatinda degil.", e);
                typingElement.textContent = "Developer";
            }
        }
    }

    //---------------------------------
    // CHATBOT ISLEVSELLIGI (GUNCEL VE DUZELTILMIS KOD)
    //---------------------------------
    const chatbotForm = document.getElementById('chatbot-form');
    const chatbotInput = document.getElementById('chatbot-input');
    const chatbotMessages = document.getElementById('chatbot-messages');

    if (chatbotForm) {
        chatbotForm.addEventListener('submit', async (e) => {
            // 1. Sayfanin yenilenmesini engelle
            e.preventDefault();

            // 2. Mesaji al
            const userMessage = chatbotInput.value.trim();
            if (userMessage === "") return;

            // 3. Kullanici mesajini ekrana bas ve input'u temizle
            addMessage('user', userMessage);
            chatbotInput.value = "";

            // 4. "Yaziyor..." mesaji ekle
            const loadingMessage = addMessage('bot', '...');

            try {
                // 5. Backend'e '/chat' rotasina istek at
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: userMessage })
                });

                if (!response.ok) {
                    throw new Error('Sunucu yanit vermedi');
                }

                const data = await response.json();

                // 6. KRITIK DUZELTME: 'data.response' DEGIL, 'data.reply'
                // "..." mesajini gercek cevapla guncelle
                loadingMessage.querySelector('p').textContent = data.reply;

            } catch (error) {
                console.error("Chatbot hatasi:", error);
                // Hata olursa "..." mesajini hata mesajiyla guncelle
                loadingMessage.querySelector('p').textContent = "Uzgunum, bir sorun olustu."; // Turkce karakter kaldirildi
            }
        });
    }

    // GUNCEL addMessage FONKSIYONU
    // Bu fonksiyon, 'user' veya 'bot' alir ve uygun class'i kendi ekler
    function addMessage(sender, text) {
        if (!chatbotMessages) return; // Guvenlik kontrolu

        const messageElement = document.createElement('div');
        messageElement.classList.add('message');

        const textElement = document.createElement('p');
        textElement.textContent = text;

        if (sender === 'user') {
            messageElement.classList.add('user-message');
        } else {
            messageElement.classList.add('bot-message');
        }

        messageElement.appendChild(textElement);
        chatbotMessages.appendChild(messageElement);

        // Pencereyi en alta kaydir
        chatbotMessages.scrollTop = chatbotMessages.scrollHeight;

        // "Yaziyor..." mesajini guncelleyebilmek icin elementi geri dondur
        return messageElement;
    }
});