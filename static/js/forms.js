document.addEventListener("DOMContentLoaded", () => {
    if (!window.Choices) {
        return;
    }

    document.querySelectorAll("select:not([data-native-select])").forEach((select) => {
        if (select.dataset.enhanced === "true") {
            return;
        }

        const hasManyOptions = select.options.length > 7;

        new window.Choices(select, {
            allowHTML: false,
            itemSelectText: "",
            noChoicesText: "No options available",
            noResultsText: "No matching options",
            removeItemButton: select.multiple,
            searchEnabled: hasManyOptions,
            searchPlaceholderValue: "Search options",
            shouldSort: false,
        });

        select.dataset.enhanced = "true";
    });
});
