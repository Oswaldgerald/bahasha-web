document.addEventListener("DOMContentLoaded", () => {
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
