document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const navigation = document.querySelector("#main-navigation");
    const mobileToggle = document.querySelector('[data-action="toggle-navigation"]');
    const closeButton = document.querySelector('[data-action="close-navigation"]');
    const collapseButton = document.querySelector('[data-action="collapse-sidebar"]');
    const mobileViewport = window.matchMedia("(max-width: 760px)");

    if (!navigation || !mobileToggle) {
        return;
    }

    const closeMobileNavigation = () => {
        body.classList.remove("navigation-open");
        mobileToggle.setAttribute("aria-expanded", "false");
    };

    const openMobileNavigation = () => {
        body.classList.add("navigation-open");
        mobileToggle.setAttribute("aria-expanded", "true");
    };

    mobileToggle.addEventListener("click", () => {
        if (body.classList.contains("navigation-open")) {
            closeMobileNavigation();
        } else {
            openMobileNavigation();
        }
    });

    closeButton?.addEventListener("click", closeMobileNavigation);

    navigation.addEventListener("click", (event) => {
        if (mobileViewport.matches && event.target.closest("a")) {
            closeMobileNavigation();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            closeMobileNavigation();
        }
    });

    if (collapseButton) {
        try {
            if (localStorage.getItem("bahasha-sidebar-collapsed") === "true") {
                body.classList.add("sidebar-collapsed");
            }
        } catch (_error) {
            // Storage can be unavailable in privacy-restricted browsers.
        }

        const syncCollapseState = () => {
            const isCollapsed = body.classList.contains("sidebar-collapsed");
            collapseButton.setAttribute("aria-expanded", String(!isCollapsed));
            collapseButton.title = isCollapsed ? "Expand sidebar" : "Collapse sidebar";
        };

        collapseButton.addEventListener("click", () => {
            const isCollapsed = body.classList.toggle("sidebar-collapsed");
            try {
                localStorage.setItem("bahasha-sidebar-collapsed", String(isCollapsed));
            } catch (_error) {
                // The visual state still works when storage is unavailable.
            }
            syncCollapseState();
        });

        syncCollapseState();
    }

    mobileViewport.addEventListener("change", closeMobileNavigation);
});
