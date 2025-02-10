// Ensure ABOPUtility is properly assigned to the global window object
window.ABOPUtility = (() => {
    function attachEventListeners() {
        console.log("Attaching ABOP event listeners...");
        setupCheckboxListeners();
        setupInputGroupListeners();
    }

    function setupCheckboxListeners() {
        document.addEventListener("change", function (event) {
            if (event.target.matches("input[type='checkbox']")) {
                updateInputGroupState();
            }
        });

        console.log("Checkbox listeners attached.");
        updateInputGroupState();
    }

    function updateInputGroupState() {
        console.log("Running updateInputGroupState...");

        let moveToFillCheckbox = document.getElementById("move_fill");
        let otherCheckboxes = [document.getElementById("sell_rx"), document.getElementById("abop")];
        let inputGroups = document.querySelectorAll(".input-group");

        if (!moveToFillCheckbox || inputGroups.length === 0) {
            console.error("Required elements not found.");
            return;
        }

        let otherChecked = otherCheckboxes.some(cb => cb && cb.checked);
        inputGroups.forEach(inputGroup => {
            if (moveToFillCheckbox.checked && !otherChecked) {
                inputGroup.classList.add("disabled");
                inputGroup.querySelectorAll("input, button").forEach(el => el.disabled = true);
            } else {
                inputGroup.classList.remove("disabled");
                inputGroup.querySelectorAll("input, button").forEach(el => el.disabled = false);
            }
        });
    }

    function setupInputGroupListeners() {
        document.addEventListener("click", function (event) {
            if (event.target.classList.contains("plus-btn")) {
                addInputGroup(event.target);
            }
            if (event.target.classList.contains("minus-btn")) {
                removeInputGroup(event.target);
            }
        });

        console.log("Input group listeners attached.");
    }

    function addInputGroup(button) {
        const inputGroupsContainer = document.getElementById("input-groups");
        if (!inputGroupsContainer) {
            console.error("Input groups container not found.");
            return;
        }

        const newGroup = button.closest(".input-group").cloneNode(true);

        // Reset input values
        newGroup.querySelectorAll("input").forEach(input => input.value = "");

        inputGroupsContainer.appendChild(newGroup);
        updateInputGroupState();
    }

    function removeInputGroup(button) {
        if (document.querySelectorAll(".input-group").length > 1) {
            button.closest(".input-group").remove();
            updateInputGroupState();
        } else {
            alert("At least one input group must remain.");
        }
    }

    return {
        init: function () {
            console.log("Initializing ABOP Utility...");
            attachEventListeners();
        }
    };
})();
