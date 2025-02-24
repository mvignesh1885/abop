window.PuttyLauncher = (() => {
    function attachEventListeners() {
        document.getElementById("putty-env-dropdown").addEventListener("change", updateStoreNumberState);
        document.getElementById("launch-putty-btn").addEventListener("click", sendPuttyRequest);
    }

    function updateStoreNumberState() {
        let envDropdown = document.getElementById("putty-env-dropdown");
        let storeNumberField = document.getElementById("putty-store-number");

        if (envDropdown.value === "Local") {
            storeNumberField.disabled = false;
        } else {
            storeNumberField.value = "";
            storeNumberField.disabled = true;
        }
    }

    function sendPuttyRequest() {
        let environment = document.getElementById("putty-env-dropdown").value;
        let storeNumber = document.getElementById("putty-store-number").value;
        let statusDiv = document.getElementById("putty-status");

        if (!environment) {
            statusDiv.innerHTML = `<p style="color:red;">Please select an environment.</p>`;
            return;
        }

        let requestData = {
            "ENVIRONMENT": environment,
            "STORE_NUMBER": storeNumber
        };

        console.log("Sending request to launch Putty:", requestData);

        fetch("/launch_putty", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(requestData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                statusDiv.innerHTML = `<p style="color:red;">Error: ${data.error}</p>`;
            } else {
                statusDiv.innerHTML = `<p style="color:green;">Putty Launched Successfully.</p>`;
            }
        })
        .catch(error => {
            console.error("Error:", error);
            statusDiv.innerHTML = `<p style="color:red;">Failed to connect to backend.</p>`;
        });
    }

    return {
        init: function () {
            console.log("Initializing Putty Launcher...");
            attachEventListeners();
        }
    };
})();
