window.ABOPUtility = (() => {
    function attachEventListeners() {
        console.log("Attaching ABOP event listeners...");
        setupCheckboxListeners();
        setupInputGroupListeners();
        setupSubmitListener(); // Attach submit event listener
    }

    function setupSubmitListener() {
        document.getElementById("submit-btn").addEventListener("click", function () {
            sendFormData();
        });
    }

    function sendFormData() {
        let environment = document.getElementById("env-dropdown").value;
        let storeNumber = document.getElementById("store-number").value;
    
        let rxDetails = [];
        document.querySelectorAll(".input-group").forEach(group => {
            let rxNbr = group.querySelector(".rx-nbr").value;
            let fillNbr = group.querySelector(".fill-nbr").value;
            let fillDisp = group.querySelector(".fill-disp").value;
            rxDetails.push({ "rx_nbr": rxNbr, "fill_nbr": fillNbr, "fill_dsp": fillDisp });
        });
    
        let sellSelected = document.getElementById("sell_rx").checked;
        let moveToFillSelected = document.getElementById("move_fill").checked;
        let generateAbopSelected = document.getElementById("abop").checked;
    
        let formData = {
            "ENVIRONMENT": environment,
            "STORE_NUMBER": storeNumber,
            "rx_details": rxDetails,
            "sell_selected": sellSelected,
            "move_to_fill_selected": moveToFillSelected,
            "generate_abop_selected": generateAbopSelected
        };
    
        console.log("Sending data to backend:", formData);
    
        fetch("/run_move_to_fill", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            console.log("Response from backend:", data);
            if (data.error) {
                alert("Error: " + data.error);  // ✅ Show error alert if failure
            } else {
                alert("Process completed successfully.");  // ✅ Show success alert
            }
        })
        .catch(error => {
            console.error("Error:", error);
            alert("Failed to connect to backend.");
        });
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
        let moveToFillCheckbox = document.getElementById("move_fill");
        let otherCheckboxes = [document.getElementById("sell_rx"), document.getElementById("abop")];
        let inputGroups = document.querySelectorAll(".input-group");

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
        const newGroup = button.closest(".input-group").cloneNode(true);

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
