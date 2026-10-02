document.addEventListener("DOMContentLoaded", () => {
    const input = document.querySelector(".profile-file-input");
    const previewImage = document.querySelector("[data-preview-image]");
    const fallback = document.querySelector("[data-preview-fallback]");
    const removeCheckbox = document.querySelector('[name="remove_picture"]');

    if (!input || !previewImage || !fallback) {
        return;
    }

    let objectUrl = null;
    const originalSource = previewImage.dataset.originalSrc || "";

    const showFallback = () => {
        previewImage.hidden = true;
        fallback.hidden = false;
    };

    const showImage = (source) => {
        previewImage.src = source;
        previewImage.hidden = false;
        fallback.hidden = true;
    };

    input.addEventListener("change", () => {
        const [file] = input.files;
        if (!file || !file.type.startsWith("image/")) {
            if (originalSource) {
                showImage(originalSource);
            } else {
                showFallback();
            }
            return;
        }

        if (objectUrl) {
            URL.revokeObjectURL(objectUrl);
        }

        objectUrl = URL.createObjectURL(file);
        showImage(objectUrl);

        if (removeCheckbox) {
            removeCheckbox.checked = false;
        }
    });

    removeCheckbox?.addEventListener("change", () => {
        if (removeCheckbox.checked) {
            input.value = "";
            showFallback();
        } else if (originalSource) {
            showImage(originalSource);
        }
    });

    window.addEventListener("beforeunload", () => {
        if (objectUrl) {
            URL.revokeObjectURL(objectUrl);
        }
    });
});
