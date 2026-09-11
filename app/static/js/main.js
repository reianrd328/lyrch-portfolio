document.addEventListener("DOMContentLoaded", () => {
    initClock();
    initSearch();
    initThemeEngine();
    initSettingsCustomizer();
});

// Unified Theme Engine
function applyTheme(themeName, customPrimary = null, customSecondary = null) {
    if (!themeName) return;
    document.documentElement.setAttribute("data-theme", themeName);
    document.body.setAttribute("data-theme", themeName);
    localStorage.setItem("lyrch_theme", themeName);

    if (themeName === "custom" || customPrimary || customSecondary) {
        if (customPrimary) {
            document.documentElement.style.setProperty("--custom-primary", customPrimary);
            document.documentElement.style.setProperty("--neon-cyan", customPrimary);
            document.documentElement.style.setProperty("--neon-blue", customPrimary);
            localStorage.setItem("lyrch_custom_primary", customPrimary);
        }
        if (customSecondary) {
            document.documentElement.style.setProperty("--custom-secondary", customSecondary);
            document.documentElement.style.setProperty("--neon-purple", customSecondary);
            localStorage.setItem("lyrch_custom_secondary", customSecondary);
        }
    } else {
        // Reset inline overrides for preset themes
        document.documentElement.style.removeProperty("--neon-cyan");
        document.documentElement.style.removeProperty("--neon-purple");
        document.documentElement.style.removeProperty("--neon-blue");
    }

    updateActiveThemeIndicators(themeName);
}

function updateActiveThemeIndicators(activeTheme) {
    // 1. Header theme dropdown buttons
    document.querySelectorAll(".theme-option-btn").forEach(btn => {
        if (btn.getAttribute("data-theme-name") === activeTheme) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // 2. Admin Settings visual theme selection cards
    document.querySelectorAll(".theme-select-card").forEach(card => {
        const input = card.querySelector("input[type='radio']");
        const themeVal = card.getAttribute("data-theme-val");
        if (themeVal === activeTheme) {
            card.classList.add("active");
            if (input) input.checked = true;
        } else {
            card.classList.remove("active");
            if (input) input.checked = false;
        }
    });
}

function initThemeEngine() {
    const savedTheme = localStorage.getItem("lyrch_theme");
    const customP = localStorage.getItem("lyrch_custom_primary");
    const customS = localStorage.getItem("lyrch_custom_secondary");

    if (savedTheme) {
        applyTheme(savedTheme, customP, customS);
    }

    // Top Navigation Palette Dropdown
    const themeToggleBtn = document.getElementById("themeToggleBtn");
    const themeDropdown = document.getElementById("themeDropdownMenu");

    if (themeToggleBtn && themeDropdown) {
        themeToggleBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            themeDropdown.classList.toggle("show");
        });

        document.addEventListener("click", (e) => {
            if (!themeDropdown.contains(e.target) && e.target !== themeToggleBtn) {
                themeDropdown.classList.remove("show");
            }
        });
    }

    const themeOptions = document.querySelectorAll(".theme-option-btn");
    themeOptions.forEach(btn => {
        btn.addEventListener("click", () => {
            const selectedTheme = btn.getAttribute("data-theme-name");
            applyTheme(selectedTheme);
            if (themeDropdown) themeDropdown.classList.remove("show");
        });
    });
}

// Interactive Admin Dashboard Customizer (Photo Upload & Color Theme Switcher)
function initSettingsCustomizer() {
    // 1. Theme Selection Cards in /admin/settings
    const themeCards = document.querySelectorAll(".theme-select-card");
    const customColorBox = document.getElementById("customColorPickerGroup");
    const primaryPicker = document.getElementById("customPrimaryPicker");
    const secondaryPicker = document.getElementById("customSecondaryPicker");

    themeCards.forEach(card => {
        card.addEventListener("click", (e) => {
            // Avoid double firing if clicking color inputs inside card
            if (e.target.tagName === "INPUT" && e.target.type === "color") return;

            const themeVal = card.getAttribute("data-theme-val");
            let pColor = primaryPicker ? primaryPicker.value : null;
            let sColor = secondaryPicker ? secondaryPicker.value : null;

            applyTheme(themeVal, pColor, sColor);

            if (customColorBox) {
                if (themeVal === "custom") {
                    customColorBox.style.display = "block";
                } else {
                    customColorBox.style.display = "none";
                }
            }
        });
    });

    // Custom Color Pickers Live Update
    if (primaryPicker) {
        primaryPicker.addEventListener("input", (e) => {
            const val = e.target.value;
            applyTheme("custom", val, secondaryPicker ? secondaryPicker.value : null);
            const hexDisplay = document.getElementById("customPrimaryHex");
            if (hexDisplay) hexDisplay.textContent = val;
        });
    }

    if (secondaryPicker) {
        secondaryPicker.addEventListener("input", (e) => {
            const val = e.target.value;
            applyTheme("custom", primaryPicker ? primaryPicker.value : null, val);
            const hexDisplay = document.getElementById("customSecondaryHex");
            if (hexDisplay) hexDisplay.textContent = val;
        });
    }

    // 2. Avatar Photo Live Preview & File Picker
    const avatarInput = document.getElementById("avatarInput");
    const avatarWrap = document.getElementById("avatarCustomizerWrap");
    const avatarImg = document.getElementById("avatarPreviewImg");
    const avatarStatus = document.getElementById("avatarStatusText");
    const avatarUrlInput = document.getElementById("avatarUrlInput");

    if (avatarWrap && avatarInput) {
        avatarWrap.addEventListener("click", () => {
            avatarInput.click();
        });

        // Drag & Drop onto avatar circle
        avatarWrap.addEventListener("dragover", (e) => {
            e.preventDefault();
            avatarWrap.style.transform = "scale(1.05)";
        });

        avatarWrap.addEventListener("dragleave", (e) => {
            e.preventDefault();
            avatarWrap.style.transform = "scale(1)";
        });

        avatarWrap.addEventListener("drop", (e) => {
            e.preventDefault();
            avatarWrap.style.transform = "scale(1)";
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                avatarInput.files = e.dataTransfer.files;
                handleAvatarFile(e.dataTransfer.files[0]);
            }
        });
    }

    if (avatarInput) {
        avatarInput.addEventListener("change", (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleAvatarFile(e.target.files[0]);
            }
        });
    }

    function handleAvatarFile(file) {
        if (!file) return;

        // Check if image
        if (!file.type.startsWith("image/")) {
            alert("Please select a valid image file (PNG, JPG, JPEG, WEBP, GIF, SVG).");
            return;
        }

        // Live preview with FileReader
        const reader = new FileReader();
        reader.onload = (event) => {
            if (avatarImg) {
                avatarImg.src = event.target.result;
                avatarImg.style.transition = "all 0.3s ease";
                avatarImg.style.filter = "brightness(1.2)";
                setTimeout(() => {
                    avatarImg.style.filter = "brightness(1)";
                }, 350);
            }
            if (avatarStatus) {
                const sizeKb = Math.round(file.size / 1024);
                avatarStatus.innerHTML = `<span style="color: #00ff66;"><i class="fa-solid fa-check"></i> ${file.name}</span> (${sizeKb} KB) <br><small style="color: var(--neon-cyan);">Ready to save</small>`;
            }
        };
        reader.readAsDataURL(file);
    }

    // Also support manual URL typing in avatarUrlInput
    if (avatarUrlInput && avatarImg) {
        avatarUrlInput.addEventListener("input", (e) => {
            const val = e.target.value.trim();
            if (val.startsWith("http://") || val.startsWith("https://") || val.startsWith("/static/") || val.startsWith("/uploads/")) {
                avatarImg.src = val;
                if (avatarStatus) {
                    avatarStatus.innerHTML = `<span style="color: var(--neon-cyan);"><i class="fa-solid fa-link"></i> Custom URL set</span>`;
                }
            }
        });
    }
}

// Live Digital Command Clock
function initClock() {
    const timeEl = document.getElementById("systemClock");
    const dateEl = document.getElementById("systemDate");

    function updateTime() {
        const now = new Date();
        const hours = String(now.getHours()).padStart(2, '0');
        const minutes = String(now.getMinutes()).padStart(2, '0');

        if (timeEl) {
            timeEl.textContent = `${hours}:${minutes}`;
        }

        if (dateEl) {
            const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
            const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
            const dayName = days[now.getDay()];
            const monthName = months[now.getMonth()];
            const dateNum = now.getDate();
            const year = now.getFullYear();
            dateEl.textContent = `${dayName}, ${monthName} ${dateNum}, ${year}`;
        }
    }

    updateTime();
    setInterval(updateTime, 1000);
}

// Quick In-Page Project Search Filter
function initSearch() {
    const searchInput = document.getElementById("commandSearch");
    if (!searchInput) return;

    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.toLowerCase().trim();
        const cards = document.querySelectorAll(".project-holo-card");

        cards.forEach(card => {
            const title = card.querySelector(".project-name")?.textContent.toLowerCase() || "";
            const desc = card.querySelector(".project-summary")?.textContent.toLowerCase() || "";
            const pills = Array.from(card.querySelectorAll(".tech-pill")).map(p => p.textContent.toLowerCase()).join(" ");

            if (title.includes(query) || desc.includes(query) || pills.includes(query)) {
                card.style.display = "flex";
            } else {
                card.style.display = "none";
            }
        });
    });
}

// Video Modal Control
function openVideoModal() {
    const modal = document.getElementById("videoModal");
    if (modal) {
        modal.style.display = "flex";
    }
}

function closeVideoModal() {
    const modal = document.getElementById("videoModal");
    if (modal) {
        modal.style.display = "none";
        const video = modal.querySelector("video");
        if (video) video.pause();
    }
}

// Close modal when clicking outside
window.addEventListener("click", (e) => {
    const modal = document.getElementById("videoModal");
    if (modal && e.target === modal) {
        closeVideoModal();
    }
});

