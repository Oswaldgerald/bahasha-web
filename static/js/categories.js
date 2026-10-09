document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("[data-category-color]").forEach((card) => {
        card.style.setProperty("--category-color", card.dataset.categoryColor || "#2D1B69");
    });

    const editor = document.querySelector("[data-category-editor]");
    if (!editor) {
        return;
    }

    const preview = editor.querySelector("[data-category-preview]");
    const nameInput = editor.querySelector("#id_name");
    const descriptionInput = editor.querySelector("#id_description");
    const iconInput = editor.querySelector("#id_icon_key");
    const colorInput = editor.querySelector("#id_theme_color");
    const colorValue = editor.querySelector("[data-color-value]");

    const updatePreview = () => {
        const color = colorInput?.value || "#2D1B69";
        preview?.style.setProperty("--category-color", color);
        if (colorValue) {
            colorValue.textContent = color.toUpperCase();
        }

        const name = preview?.querySelector("[data-preview-name]");
        const description = preview?.querySelector("[data-preview-description]");
        if (name) {
            name.textContent = nameInput?.value.trim() || "Category";
        }
        if (description) {
            description.textContent = descriptionInput?.value.trim() || "Contribution category";
        }

        const currentIcon = preview?.querySelector("svg, [data-lucide]");
        if (currentIcon && iconInput?.value) {
            const replacement = document.createElement("i");
            replacement.setAttribute("data-lucide", iconInput.value);
            replacement.setAttribute("aria-hidden", "true");
            currentIcon.replaceWith(replacement);
            if (window.lucide) {
                window.lucide.createIcons({ attrs: { "stroke-width": 1.8 } });
            }
        }
    };

    [nameInput, descriptionInput, iconInput, colorInput].forEach((input) => {
        input?.addEventListener("input", updatePreview);
        input?.addEventListener("change", updatePreview);
    });
    updatePreview();
});
