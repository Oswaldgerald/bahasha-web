document.addEventListener("DOMContentLoaded", () => {
    if (!window.Choices) {
        return;
    }

    document.querySelectorAll("select:not([data-native-select])").forEach((select) => {
        if (select.dataset.enhanced === "true") {
            return;
        }

        const searchEnabled = select.dataset.searchable !== "false";

        select.choicesInstance = new window.Choices(select, {
            allowHTML: false,
            itemSelectText: "",
            noChoicesText: "No options available",
            noResultsText: "No matching options",
            removeItemButton: select.multiple,
            searchEnabled,
            searchPlaceholderValue: select.dataset.searchPlaceholder || "Type to search",
            shouldSort: false,
        });

        select.dataset.enhanced = "true";
    });
});
