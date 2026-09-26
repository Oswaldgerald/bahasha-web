document.addEventListener("DOMContentLoaded", () => {
    if (window.lucide) {
        window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
    }

    document.querySelectorAll("[data-progress]").forEach((progressBar) => {
        const rawValue = Number.parseFloat(progressBar.dataset.progress);
        const value = Number.isFinite(rawValue) ? rawValue : 0;
        progressBar.style.width = `${Math.min(100, Math.max(0, value))}%`;
    });

    document.querySelectorAll('[data-action="print"]').forEach((button) => {
        button.addEventListener("click", () => window.print());
    });

});
