document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-password-toggle]").forEach((button) => {
        const input = document.getElementById(button.dataset.passwordToggle);
        if (!input) {
            return;
        }

        button.addEventListener("click", () => {
            const isVisible = input.type === "text";
            input.type = isVisible ? "password" : "text";
            button.setAttribute("aria-pressed", String(!isVisible));
            button.setAttribute("aria-label", isVisible ? "Show password" : "Hide password");
            button.innerHTML = `<i data-lucide="${isVisible ? "eye" : "eye-off"}" aria-hidden="true"></i>`;

            if (window.lucide) {
                window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
            }

            input.focus({ preventScroll: true });
        });
    });
});
