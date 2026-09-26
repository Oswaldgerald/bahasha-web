document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const navigation = document.querySelector("#main-navigation");
    const mobileToggle = document.querySelector('[data-action="toggle-navigation"]');
    const closeButton = document.querySelector('[data-action="close-navigation"]');
    const collapseButton = document.querySelector('[data-action="collapse-sidebar"]');
    const sectionToggles = navigation?.querySelectorAll('[data-action="toggle-nav-section"]') ?? [];
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

    let collapsedSections = [];
    try {
        collapsedSections = JSON.parse(localStorage.getItem("bahasha-collapsed-sections") || "[]");
    } catch (_error) {
        collapsedSections = [];
    }

    const saveCollapsedSections = () => {
        const sectionIds = Array.from(sectionToggles)
            .filter((button) => button.closest(".nav-group")?.classList.contains("is-collapsed"))
            .map((button) => button.getAttribute("aria-controls"));

        try {
            localStorage.setItem("bahasha-collapsed-sections", JSON.stringify(sectionIds));
        } catch (_error) {
            // Section toggles remain functional when storage is unavailable.
        }
    };

    sectionToggles.forEach((button) => {
        const group = button.closest(".nav-group");
        const sectionId = button.getAttribute("aria-controls");
        const containsActivePage = Boolean(group?.querySelector("a.active"));

        if (!containsActivePage && collapsedSections.includes(sectionId)) {
            group?.classList.add("is-collapsed");
            button.setAttribute("aria-expanded", "false");
        }

        button.addEventListener("click", () => {
            const isCollapsed = group?.classList.toggle("is-collapsed") ?? false;
            button.setAttribute("aria-expanded", String(!isCollapsed));
            saveCollapsedSections();
        });
    });

    mobileViewport.addEventListener("change", closeMobileNavigation);
});
