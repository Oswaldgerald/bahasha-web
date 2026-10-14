// Enhance contribution workbooks with drag-and-drop and selected-file feedback.
document.addEventListener("DOMContentLoaded", () => {
    const input = document.querySelector("[data-contribution-file-input]");
    const dropzone = document.querySelector("[data-contribution-file-dropzone]");
    const selection = document.querySelector("[data-contribution-file-selection]");
    const fileName = document.querySelector("[data-contribution-file-name]");
    const fileSize = document.querySelector("[data-contribution-file-size]");
    const removeButton = document.querySelector("[data-contribution-file-remove]");

    if (!input || !dropzone || !selection || !fileName || !fileSize) {
        return;
    }

    /** Convert byte counts into compact values suitable for the upload panel. */
    const formatFileSize = (bytes) => {
        if (bytes < 1024) {
            return `${bytes} B`;
        }
        if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toFixed(1)} KB`;
        }
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    /** Synchronize selected-file details and dropzone visual state. */
    const updateSelection = () => {
        const file = input.files?.[0];
        selection.hidden = !file;
        dropzone.classList.toggle("has-file", Boolean(file));

        if (file) {
            fileName.textContent = file.name;
            fileSize.textContent = `${formatFileSize(file.size)} · Ready to validate / Tayari kuhakikiwa`;
        } else {
            fileName.textContent = "";
            fileSize.textContent = "";
        }
    };

    input.addEventListener("change", updateSelection);

    ["dragenter", "dragover"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.add("is-dragging");
        });
    });

    ["dragleave", "drop"].forEach((eventName) => {
        dropzone.addEventListener(eventName, (event) => {
            event.preventDefault();
            dropzone.classList.remove("is-dragging");
        });
    });

    // DataTransfer assigns a dropped file to the native input so form submission
    // continues to use normal browser multipart behavior.
    dropzone.addEventListener("drop", (event) => {
        const [file] = event.dataTransfer?.files || [];
        if (!file) {
            return;
        }

        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
        input.dispatchEvent(new Event("change", { bubbles: true }));
    });

    removeButton?.addEventListener("click", () => {
        input.value = "";
        updateSelection();
        input.focus();
    });
});
