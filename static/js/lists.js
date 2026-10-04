document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-confirm-action]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirmAction)) {
                event.preventDefault();
            }
        });
    });
});
