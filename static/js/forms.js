document.addEventListener("DOMContentLoaded", () => {
    if (!window.Choices) {
        return;
    }

    document.querySelectorAll("select:not([data-native-select])").forEach((select) => {
        if (select.dataset.enhanced === "true") {
            return;
        }

        const hasManyOptions = select.options.length > 7;
        const searchEnabled = select.dataset.searchable === "true" || hasManyOptions;

        select.choicesInstance = new window.Choices(select, {
            allowHTML: false,
            itemSelectText: "",
            noChoicesText: "No options available",
            noResultsText: "No matching options",
            removeItemButton: select.multiple,
            searchEnabled,
            searchPlaceholderValue: select.dataset.searchPlaceholder || "Search options",
            shouldSort: false,
        });

        select.dataset.enhanced = "true";
    });
});
