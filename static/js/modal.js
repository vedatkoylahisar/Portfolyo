/* ==========================================================================
   PORTFOLIO MODAL LOGIC (Multi-Language Support)
   ========================================================================== */

// Global Deðiþkenler
let projectModal, modalTitle, modalDesc, modalTech, modalGithub, modalDemo, modalKaggle, projectCloseBtn;

// 1. DÝL SÖZLÜÐÜ: JS tarafýnda kullanýlacak metinler
const uiTranslations = {
    tr: {
        viewProfile: 'Profili Gor', // Türkçe
        viewProject: 'Incele',
        loading: 'Yukleniyor...',
        error: 'Hata olustu.',
        folderInfo: 'Kaggle uzerindeki proje koleksiyonum.'
    },
    en: {
        viewProfile: 'View Profile',     // Ýngilizce
        viewProject: 'View',
        loading: 'Loading...',
        error: 'Error occurred.',
        folderInfo: 'My project collection on Kaggle.'
    },
    de: {
        viewProfile: 'Profil ansehen',   // Almanca
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
    modalTech = document.getElementById("modalTech");
    modalGithub = document.getElementById("modalGithub");
    modalDemo = document.getElementById("modalDemo");
    modalKaggle = document.getElementById("modalKaggle");
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

    // 2. MEVCUT DÝLÝ ALGILA
    // HTML etiketindeki lang özelliðini okur (Örn: <html lang="en">)
    // Eðer bulamazsa varsayýlan olarak 'en' seçer.
    const currentLang = document.documentElement.lang || 'en';

    // O dile ait metinleri seç, yoksa Ýngilizce'yi al
    const t = uiTranslations[currentLang] || uiTranslations['en'];

    // Verileri HTML'den Çek
    const type = element.getAttribute("data-type");
    const title = element.getAttribute("data-title");
    const desc = element.getAttribute("data-desc");
    const tech = element.getAttribute("data-tech");
    const subProjectsRaw = element.getAttribute("data-subprojects");
    const kaggleUrl = element.getAttribute("data-kaggle");

    // Baþlýðý ve Teknolojileri Doldur
    modalTitle.innerHTML = type === 'folder' ? '<i class="fas fa-folder-open"></i> ' + title : title;

    modalTech.innerHTML = "";
    if (tech && tech !== "None") {
        tech.split(',').forEach(item => {
            if (item.trim()) {
                let tag = document.createElement("span");
                tag.className = "tech-tag";
                tag.innerText = item.trim();
                modalTech.appendChild(tag);
            }
        });
    }

    // --- KLASÖR MANTIÐI ---
    if (type === 'folder') {
        let listHtml = `<p style="margin-bottom: 20px; color: #ccc;">${desc}</p>`;

        try {
            const subProjects = JSON.parse(subProjectsRaw || "[]");

            if (subProjects.length > 0) {
                listHtml += `<div class="kaggle-list">`;

                subProjects.forEach(proj => {
                    // DÝNAMÝK METÝN KULLANIMI: t.viewProject
                    listHtml += `
                        <div class="kaggle-item">
                            <div class="k-info">
                                <span class="k-title"><i class="fas fa-code"></i> ${proj.title}</span>
                                <span class="k-desc">${proj.description ? proj.description.substring(0, 60) + '...' : ''}</span>
                            </div>
                            <a href="${proj.url}" target="_blank" class="btn-kaggle-mini">
                                ${t.viewProject} <i class="fas fa-arrow-right"></i>
                            </a>
                        </div>
                    `;
                });
                listHtml += `</div>`;
            } else {
                listHtml += `<p>${t.error}</p>`;
            }
        } catch (e) {
            console.error("JSON Hatasý:", e);
            listHtml += `<p>${t.error}</p>`;
        }

        modalDesc.innerHTML = listHtml;

        // Butonlarý Gizle/Göster
        if (modalGithub) modalGithub.style.display = "none";
        if (modalDemo) modalDemo.style.display = "none";

        if (modalKaggle) {
            modalKaggle.style.display = "inline-flex";
            modalKaggle.href = kaggleUrl;
            // DÝNAMÝK METÝN KULLANIMI: t.viewProfile
            modalKaggle.innerHTML = `<i class="fab fa-kaggle"></i> ${t.viewProfile}`;
            modalKaggle.style.marginTop = "15px";
        }

    }
    // --- NORMAL PROJE ---
    else {
        modalDesc.innerHTML = desc;

        const github = element.getAttribute("data-github");
        const demo = element.getAttribute("data-demo");

        updateModalButton(modalGithub, github);
        updateModalButton(modalDemo, demo);

        if (modalKaggle) modalKaggle.style.display = "none";
    }

    // Göster
    projectModal.style.display = "block";
    document.body.style.overflow = "hidden";
}

function updateModalButton(btn, link) {
    if (btn) {
        if (link && link !== "None" && link !== "") {
            btn.style.display = "inline-flex";
            btn.href = link;
        } else {
            btn.style.display = "none";
        }
    }
}