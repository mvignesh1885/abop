window.ABOPUtility = (() => {
    function attachEventListeners() {
        console.log("Attaching ABOP event listeners...");
        setupCheckboxListeners();
        setupInputGroupListeners();
        setupSubmitListener(); // Attach submit event listener
    }

    function setupSubmitListener() {
        document.getElementById("submit-btn").addEventListener("click", function () {
            let statusDiv = document.getElementById("status");
    
            // ✅ Stop any existing log stream
            if (window.eventSource) {
                window.eventSource.close();
            }
    
            // ✅ Clear previous logs completely
            statusDiv.innerHTML = "Starting process...<br>";
    
            sendFormData(); // Send the form data after clearing logs
        });
    }

    function startLogStream() {
		console.log("Starting real-time log streaming...");
		let statusDiv = document.getElementById("status");
	
		// ✅ Close any existing event stream before creating a new one
		if (window.eventSource) {
			window.eventSource.close();
		}
	
		window.eventSource = new EventSource("/stream_logs");
	
		window.eventSource.onmessage = function(event) {
			let logMessage = event.data.trim();
    
            // Prevent "Process completed successfully" from replacing logs
            if (logMessage && logMessage !== "Process completed successfully") {
                let logElement = document.createElement("p");
                logElement.textContent = logMessage;
                statusDiv.appendChild(logElement);
                statusDiv.scrollTop = statusDiv.scrollHeight; // Auto-scroll
            }
        };
	
		window.eventSource.onerror = function() {
			console.error("Log stream error. Attempting to reconnect...");
			window.eventSource.close();
			setTimeout(startLogStream, 3000);  // ✅ Reconnect after 3 seconds
		};
	}

    function sendFormData() {
        let environment = document.getElementById("env-dropdown").value;
        let storeNumber = document.getElementById("store-number").value;
    
        let rxDetails = [];
        document.querySelectorAll(".input-group").forEach(group => {
            let rxNbr = group.querySelector(".rx-nbr");
            let fillNbr = group.querySelector(".fill-nbr");
            let fillDisp = group.querySelector(".fill-disp");

            if (!rxNbr.disabled) {
                rxDetails.push({ 
                    "rx_nbr": rxNbr.value.trim(), 
                    "fill_nbr": fillNbr.value.trim(), 
                    "fill_dsp": fillDisp.value.trim() 
                });
            } else {
                // ✅ Clear values from disabled fields
                rxNbr.value = "";
                fillNbr.value = "";
                fillDisp.value = "";
            }
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
        
        startLogStream(); 

        fetch("/run_move_to_fill", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(data => {
            console.log("Response from backend:", data);
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
                inputGroup.querySelectorAll("input, button").forEach(el => {
                    el.disabled = true;
                    el.value = "";  // ✅ Clear values from disabled fields
                });
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
