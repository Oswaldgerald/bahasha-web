document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-progress]").forEach((progressBar) => {
        const rawValue = Number.parseFloat(progressBar.dataset.progress);
        const value = Number.isFinite(rawValue) ? rawValue : 0;
        progressBar.style.width = `${Math.min(100, Math.max(0, value))}%`;
    });

    document.querySelectorAll('[data-action="print"]').forEach((button) => {
        button.addEventListener("click", () => window.print());
    });

    const navigationToggle = document.querySelector('[data-action="toggle-navigation"]');
    const navigation = document.querySelector("#main-navigation");

    if (navigationToggle && navigation) {
        navigationToggle.addEventListener("click", () => {
            const isOpen = document.body.classList.toggle("navigation-open");
            navigationToggle.setAttribute("aria-expanded", String(isOpen));
            navigationToggle.textContent = isOpen ? "Close menu" : "Menu";
        });

        navigation.addEventListener("click", (event) => {
            if (event.target.closest("a") && window.matchMedia("(max-width: 640px)").matches) {
                document.body.classList.remove("navigation-open");
                navigationToggle.setAttribute("aria-expanded", "false");
                navigationToggle.textContent = "Menu";
            }
        });
    }
});
