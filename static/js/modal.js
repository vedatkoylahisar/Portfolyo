/* ==========================================================================
   PORTFOLIO MODAL LOGIC (Multi-Language Support & Fixes)
   ========================================================================== */

// Global Deðiþkenler
let projectModal, modalTitle, modalDesc, modalTech, modalGithub, modalDemo, modalProfile, modalSubProjectsList, projectCloseBtn;

// 1. DÝL SÖZLÜÐÜ
const uiTranslations = {
    tr: {
        viewProfile: 'Profili Gor',
        viewProject: 'Incele',
        loading: 'Yukleniyor...',
        error: 'Hata olustu.',
        folderInfo: 'Kaggle uzerindeki proje koleksiyonum.'
    },
    en: {
        viewProfile: 'View Profile',
        viewProject: 'View',
        loading: 'Loading...',
        error: 'Error occurred.',
        folderInfo: 'My project collection on Kaggle.'
    },
    de: {
        viewProfile: 'Profil ansehen',
        viewProject: 'Ansehen',
        loading: 'Laden...',
        error: 'Fehler aufgetreten.',
        folderInfo: 'Meine Projektsammlung auf Kaggle.'
    }
};

// Sayfa Yüklendiðinde
document.addEventListener("DOMContentLoaded", () => {
    projectModal = document.getElementById("projectModal");
    modalTitle = document.getElementById("modalTitle");
    modalDesc = document.getElementById("modalDesc");
    modalTech = document.getElementById("modalTech"); // Etiket Konteyneri
    modalSubProjectsList = document.getElementById("modalSubProjects"); // Kaggle Listesi Konteyneri

    // Butonlar
    modalGithub = document.getElementById("modalGithub");
    modalDemo = document.getElementById("modalDemo");
    modalProfile = document.getElementById("modalProfile"); // HTML'deki ID ile eþleþti

    projectCloseBtn = document.querySelector("#projectModal .close-btn");

    if (projectCloseBtn) {
        projectCloseBtn.onclick = closeProjectModal;
    }

    window.addEventListener('click', (event) => {
        if (event.target === projectModal) {
            closeProjectModal();
        }
    });
});

function closeProjectModal() {
    if (projectModal) {
        projectModal.style.display = "none";
        document.body.style.overflow = "auto";
    }
}

function openModal(element) {
    if (!projectModal) return;

    // 2. DÝLÝ ALGILA
    const currentLang = document.documentElement.lang || 'en';
    const t = uiTranslations[currentLang] || uiTranslations['en'];

    // 3. VERÝLERÝ HTML'DEN ÇEK (data- attributes)
    const type = element.getAttribute("data-type");
    const title = element.getAttribute("data-title");
    const desc = element.getAttribute("data-desc");

    // HTML'de data-url olarak göndermiþtik, onu alýyoruz
    const profileUrl = element.getAttribute("data-url");

    // Linkler
    const githubLink = element.getAttribute("data-github");
    const demoLink = element.getAttribute("data-demo");

    // JSON Veriler (Tags ve SubProjects)
    let tags = [];
    let subProjects = [];
    try {
        tags = JSON.parse(element.getAttribute("data-tags") || "[]");
    } catch (e) { console.error("Tags parse error", e); }

    try {
        subProjects = JSON.parse(element.getAttribute("data-subprojects") || "[]");
    } catch (e) { console.error("Subprojects parse error", e); }


    // --- A. ÝÇERÝÐÝ DOLDUR ---

    // Baþlýk
    modalTitle.innerHTML = type === 'folder' ? '<i class="fas fa-folder-open" style="color:#00d9ff"></i> ' + title : title;

    // Açýklama
    modalDesc.innerHTML = desc;

    // Etiketler (Tags)
    modalTech.innerHTML = "";
    tags.forEach(tag => {
        let span = document.createElement("span");
        span.className = "project-tag"; // CSS'teki class ile uyumlu
        span.innerText = tag;
        modalTech.appendChild(span);
    });


    // --- B. GÖRÜNÜM MANTIÐI (FOLDER vs PROJECT) ---

    // Temizlik: Önce listeyi temizle
    if (modalSubProjectsList) modalSubProjectsList.innerHTML = "";
    if (modalSubProjectsList) modalSubProjectsList.style.display = "none";

    if (type === 'folder') {
        // --- KLASÖR (KAGGLE) MODU ---

        // 1. GitHub ve Demo butonlarýný gizle
        updateModalButton(modalGithub, null);
        updateModalButton(modalDemo, null);

        // 2. Profil Butonunu Göster (En Altta)
        if (modalProfile) {
            modalProfile.style.display = "inline-flex";
            modalProfile.href = profileUrl;
            modalProfile.innerHTML = `<i class="fas fa-user-circle"></i> ${t.viewProfile}`;
        }

        // 3. Kaggle Listesini Oluþtur ve Göster
        if (subProjects.length > 0 && modalSubProjectsList) {
            modalSubProjectsList.style.display = "flex"; // Listeyi görünür yap

            subProjects.forEach(proj => {
                const itemDiv = document.createElement("div");
                itemDiv.className = "kaggle-item"; // CSS class

                // Link kontrolü
                const itemLink = proj.url || proj.link || "#";

                itemDiv.innerHTML = `
                    <div class="k-info">
                        <strong><i class="fas fa-code"></i> ${proj.title || "Project"}</strong>
                        <div class="k-desc" style="font-size:0.8rem; color:#aaa;">${proj.description ? proj.description.substring(0, 50) + '...' : ''}</div>
                    </div>
                    <a href="${itemLink}" target="_blank" class="btn-kaggle-mini">
                        ${t.viewProject} <i class="fas fa-arrow-right"></i>
                    </a>
                `;
                modalSubProjectsList.appendChild(itemDiv);
            });
        }

    } else {
        // --- NORMAL PROJE MODU ---

        // 1. Profil butonunu ve Listeyi gizle
        if (modalProfile) modalProfile.style.display = "none";
        if (modalSubProjectsList) modalSubProjectsList.style.display = "none";

        // 2. GitHub ve Demo butonlarýný ayarla
        updateModalButton(modalGithub, githubLink);
        updateModalButton(modalDemo, demoLink);
    }

    // Modalý Aç
    projectModal.style.display = "block";
    document.body.style.overflow = "hidden"; // Arka plan kaymasýný engelle
}

// Yardýmcý Fonksiyon: Buton Göster/Gizle
function updateModalButton(btn, link) {
    if (btn) {
        if (link && link !== "None" && link !== "" && link !== "#") {
            btn.style.display = "inline-flex";
            btn.href = link;
        } else {
            btn.style.display = "none";
        }
    }
}