// Initialize icon placeholders used by Django administration customizations.
document.addEventListener("DOMContentLoaded", () => {
    if (window.lucide) {
        window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
    }
});
