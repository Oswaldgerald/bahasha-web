document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-confirm-user-action]").forEach((form) => {
        form.addEventListener("submit", (event) => {
            if (!window.confirm(form.dataset.confirmUserAction)) {
                event.preventDefault();
            }
        });
    });
});
