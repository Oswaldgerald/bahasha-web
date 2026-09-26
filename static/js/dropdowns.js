document.addEventListener("DOMContentLoaded", () => {
    const dropdowns = document.querySelectorAll("[data-dropdown]");

    const closeDropdown = (dropdown, restoreFocus = false) => {
        const trigger = dropdown.querySelector('[data-action="toggle-dropdown"]');
        const menu = dropdown.querySelector('[role="menu"]');

        dropdown.classList.remove("is-open");
        trigger?.setAttribute("aria-expanded", "false");
        menu?.setAttribute("aria-hidden", "true");

        if (restoreFocus) {
            trigger?.focus();
        }
    };

    dropdowns.forEach((dropdown) => {
        const trigger = dropdown.querySelector('[data-action="toggle-dropdown"]');
        const menu = dropdown.querySelector('[role="menu"]');

        if (!trigger || !menu) {
            return;
        }

        trigger.addEventListener("click", () => {
            const willOpen = !dropdown.classList.contains("is-open");
            dropdowns.forEach((item) => closeDropdown(item));

            if (willOpen) {
                dropdown.classList.add("is-open");
                trigger.setAttribute("aria-expanded", "true");
                menu.setAttribute("aria-hidden", "false");
            }
        });
    });

    document.addEventListener("click", (event) => {
        dropdowns.forEach((dropdown) => {
            if (!dropdown.contains(event.target)) {
                closeDropdown(dropdown);
            }
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") {
            return;
        }

        dropdowns.forEach((dropdown) => {
            if (dropdown.classList.contains("is-open")) {
                closeDropdown(dropdown, true);
            }
        });
    });
});
