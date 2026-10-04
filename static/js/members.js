document.addEventListener("DOMContentLoaded", () => {
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
