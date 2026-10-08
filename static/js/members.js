document.addEventListener("DOMContentLoaded", () => {
    const csvInput = document.querySelector("[data-member-csv-input]");
    const csvDropzone = document.querySelector("[data-member-csv-dropzone]");
    const csvSelection = document.querySelector("[data-member-csv-selection]");
    const csvName = document.querySelector("[data-member-csv-name]");
    const csvSize = document.querySelector("[data-member-csv-size]");
    const csvRemove = document.querySelector("[data-member-csv-remove]");

    const formatFileSize = (bytes) => {
        if (bytes < 1024) {
            return `${bytes} B`;
        }
        if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toFixed(1)} KB`;
        }
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const updateCsvSelection = () => {
        const file = csvInput?.files?.[0];
        if (!csvSelection || !csvName || !csvSize) {
            return;
        }

        csvSelection.hidden = !file;
        csvDropzone?.classList.toggle("has-file", Boolean(file));
        if (file) {
            csvName.textContent = file.name;
            csvSize.textContent = `${formatFileSize(file.size)} · Ready to upload / Tayari kupakiwa`;
        } else {
            csvName.textContent = "";
            csvSize.textContent = "";
        }
    };

    csvInput?.addEventListener("change", updateCsvSelection);

    if (csvDropzone && csvInput) {
        ["dragenter", "dragover"].forEach((eventName) => {
            csvDropzone.addEventListener(eventName, (event) => {
                event.preventDefault();
                csvDropzone.classList.add("is-dragging");
            });
        });

        ["dragleave", "drop"].forEach((eventName) => {
            csvDropzone.addEventListener(eventName, (event) => {
                event.preventDefault();
                csvDropzone.classList.remove("is-dragging");
            });
        });

        csvDropzone.addEventListener("drop", (event) => {
            const [file] = event.dataTransfer?.files || [];
            if (!file) {
                return;
            }
            const transfer = new DataTransfer();
            transfer.items.add(file);
            csvInput.files = transfer.files;
            csvInput.dispatchEvent(new Event("change", { bubbles: true }));
        });
    }

    csvRemove?.addEventListener("click", () => {
        csvInput.value = "";
        updateCsvSelection();
        csvInput.focus();
    });

    const photoInput = document.querySelector("[data-member-photo-input]");
    const photoImage = document.querySelector("[data-member-photo-image]");
    const photoFallback = document.querySelector("[data-member-photo-fallback]");
    const removePhoto = document.querySelector('[name="remove_picture"]');
    let photoObjectUrl = null;

    const showPhotoFallback = () => {
        if (photoImage && photoFallback) {
            photoImage.hidden = true;
            photoFallback.hidden = false;
        }
    };

    const showPhoto = (source) => {
        if (photoImage && photoFallback) {
            photoImage.src = source;
            photoImage.hidden = false;
            photoFallback.hidden = true;
        }
    };

    photoInput?.addEventListener("change", () => {
        const [file] = photoInput.files;
        if (!file?.type.startsWith("image/")) {
            const originalSource = photoImage?.dataset.originalSrc;
            originalSource ? showPhoto(originalSource) : showPhotoFallback();
            return;
        }
        if (photoObjectUrl) {
            URL.revokeObjectURL(photoObjectUrl);
        }
        photoObjectUrl = URL.createObjectURL(file);
        showPhoto(photoObjectUrl);
        if (removePhoto) {
            removePhoto.checked = false;
        }
    });

    removePhoto?.addEventListener("change", () => {
        if (removePhoto.checked) {
            photoInput.value = "";
            showPhotoFallback();
        } else if (photoImage?.dataset.originalSrc) {
            showPhoto(photoImage.dataset.originalSrc);
        }
    });

    window.addEventListener("beforeunload", () => {
        if (photoObjectUrl) {
            URL.revokeObjectURL(photoObjectUrl);
        }
    });

    document.querySelectorAll("[data-confirm-rejection]").forEach((button) => {
        button.addEventListener("click", (event) => {
            const memberName = button.dataset.confirmRejection;
            const confirmed = window.confirm(
                `Reject ${memberName}? Their member record and login account will be disabled.`
            );

            if (!confirmed) {
                event.preventDefault();
            }
        });
    });

    const memberForm = document.querySelector("[data-jumuiya-url]");
    const churchSelect = document.querySelector("[data-member-church]");
    const jumuiyaSelect = document.querySelector("[data-member-jumuiya]");
    const groupSelect = document.querySelector("[data-member-groups]");

    if (!memberForm || !churchSelect || !jumuiyaSelect) {
        return;
    }

    churchSelect.addEventListener("change", async () => {
        const endpoint = new URL(memberForm.dataset.jumuiyaUrl, window.location.origin);
        endpoint.searchParams.set("church_id", churchSelect.value);

        try {
            const response = await fetch(endpoint, {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            if (!response.ok) {
                throw new Error("Unable to load Jumuiya options.");
            }

            const data = await response.json();
            const options = [
                { value: "", label: "Select Jumuiya", selected: true },
                ...data.options,
            ];

            if (jumuiyaSelect.choicesInstance) {
                jumuiyaSelect.choicesInstance.clearChoices();
                jumuiyaSelect.choicesInstance.setChoices(options, "value", "label", true);
            } else {
                jumuiyaSelect.replaceChildren(
                    ...options.map((option) => new Option(option.label, option.value, option.selected, option.selected))
                );
            }

            if (groupSelect?.choicesInstance) {
                groupSelect.choicesInstance.clearChoices();
                groupSelect.choicesInstance.setChoices(
                    data.groups.length
                        ? data.groups
                        : [{ value: "", label: "No active groups", disabled: true }],
                    "value",
                    "label",
                    true
                );
            } else if (groupSelect) {
                groupSelect.replaceChildren(
                    ...data.groups.map((group) => new Option(group.label, group.value))
                );
            }
        } catch (error) {
            jumuiyaSelect.choicesInstance?.clearChoices();
            jumuiyaSelect.choicesInstance?.setChoices(
                [{ value: "", label: "Unable to load Jumuiya", disabled: true }],
                "value",
                "label",
                true
            );
            groupSelect?.choicesInstance?.clearChoices();
            groupSelect?.choicesInstance?.setChoices(
                [{ value: "", label: "Unable to load groups", disabled: true }],
                "value",
                "label",
                true
            );
        }
    });
});
