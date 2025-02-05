import paramiko
import json
import requests
import os
from bs4 import BeautifulSoup
import logging
import urllib3  # Import urllib3 for disabling warnings
import time
from datetime import datetime, timedelta
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Suppress only the single InsecureRequestWarning from urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config(config_path):
    """
    Load the configuration from config.json
    """
    try:
        with open(config_path, 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from config file: {e}")
        return None

# Step 1: Execute Sell Service
def perform_sell_service(env, store_number, rx_details):
    """
    Perform the sell service for multiple RX details sequentially.

    Parameters:
        env (str): Environment (e.g., 'Sys1', 'Sys2').
        store_number (str): Store number.
        rx_details (list of dict): List of RX details, each containing 'rx_nbr', 'fill_nbr', and 'fill_dsp'.

    Returns:
        dict: Dictionary of results for each RX.
    """
    results = {}

    try:

        env = env.capitalize()

        for idx, rx in enumerate(rx_details, 1):
            rx_nbr = rx["rx_nbr"]
            fill_nbr = rx["fill_nbr"]
            fill_dsp = rx["fill_dsp"]

            # Construct the URL for the sell service
            url = f"https://rmps.walgreens.com/cgi-bin/possim.cgi?env={env}&store={store_number}&rxnbr={rx_nbr}&fillnbr={fill_nbr}&fillpart=0&filldsp={fill_dsp}&patresp=A&action=sell"
            logging.debug(f"Calling URL for RX {idx}: {url}")

            # Make the HTTP request
            try:
                response = requests.get(url, verify=False)  # Bypassing SSL verification for testing
                if response.status_code == 200:
                    if "The sell service has executed successfully" in response.text:
                        logging.info(f"Sell service executed successfully for RX {idx}.")
                        results[f"RX_{idx}"] = f"Success: RX {rx_nbr} sold."
                    else:
                        logging.warning(f"Unexpected response for RX {idx}: {response.text}")
                        results[f"RX_{idx}"] = f"Warning: Unexpected response for RX {rx_nbr}."
                else:
                    logging.error(f"Failed HTTP request for RX {idx}. Status code: {response.status_code}")
                    results[f"RX_{idx}"] = f"Error: HTTP {response.status_code}."
            except requests.exceptions.RequestException as e:
                logging.error(f"Error during HTTP request for RX {idx}: {e}")
                results[f"RX_{idx}"] = f"Error: {e}."

            # Log the result of the current request before proceeding
            logging.debug(f"Completed processing for RX {idx}: {results[f'RX_{idx}']}")

    except Exception as e:
        logging.error(f"Error in perform_sell_service: {e}")
        raise

    return results


def fetch_value_from_url(config_path):
    """
    Fetch password from URL using username from config.json
    """
    config = load_config(config_path)
    if not config:
        return None

    # Always use "move_to_fill" module for connectivity
    module_config = config["modules"].get("move_to_fill", {})
    username = module_config.get("username")
    shared_hostname = "tstdb01"

    if not username:
        logging.error("Username not found in configuration")
        return None

    url = f"https://rmps.walgreens.com/tools/publicPasswords/publicPassword.php?accountId=00000002392&hostName={shared_hostname}&userName={username}"
    try:
        response = requests.get(url, verify=False)  # Bypass SSL verification (use caution in production)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text()
            start = text.find("Password is: ")
            if start != -1:
                start += len("Password is: ")
                end = text.find("\n", start)
                password = text[start:end].strip()
                return password
            else:
                logging.error("Password text not found in the response")
                return None
        else:
            logging.error(f"Failed to fetch URL. HTTP Status Code: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logging.error(f"An error occurred while fetching the password: {e}")
        return None

def handle_interactive_login(shell, environment, directory=None):
    """
    Handles the interactive login process and navigates to the specified directory.
    """
    try:
        while True:
            if shell.recv_ready():
                time.sleep(2)
                output = shell.recv(4096).decode("utf-8")
                logging.debug(f"Received output: {output}")

                # Handle Sys1 specific keywords
                if environment == "sys1":
                    if "ASM" in output:
                        shell.send("N\n")
                        logging.debug("Sent 'N' for Sys1 ASM-related question.")
                        time.sleep(1)
                        output = shell.recv(1024).decode("utf-8")
                        logging.debug(f"Received output: {output}")
                    if "tstdb01" in output:
                        shell.send("Y\n")
                        logging.debug("Sent 'Y' for Sys1 target question.")
                        time.sleep(3)
                        output = shell.recv(1024).decode("utf-8")
                        logging.debug(f"Received output: {output}")

                # Handle Sys2 specific keywords
                elif environment == "sys2":
                    if "agent12c" in output:
                        shell.send("N\n")
                        logging.info("Sent 'N' for Sys2 agent12c or ASM-related question.")
                        time.sleep(1)
                        output = shell.recv(1024).decode("utf-8")
                        logging.debug(f"Received output: {output}")                  
                    if "ASM" in output:
                        shell.send("N\n")
                        logging.info("Sent 'N' for Sys2 agent12c or ASM-related question.")
                        time.sleep(1)
                        output = shell.recv(1024).decode("utf-8")
                        logging.debug(f"Received output: {output}")                  
                    if "thcicp01" in output:
                        shell.send("Y\n")
                        logging.info("Sent 'Y' for Sys2 target question.")
                        time.sleep(3)
                        output = shell.recv(1024).decode("utf-8")
                        logging.debug(f"Received output: {output}")                  
                # Check for successful login prompt
                if (environment == "sys1" and "ticpdb2" in output) or (environment == "sys2" and "thcicp01" in output):
                    logging.info("Interactive login complete.")
                    break

                # Check for errors
                if "Password locked" in output or "Access denied" in output:
                    raise ValueError("Login failed due to locked password or access issue.")
        
        if directory:
            logging.debug(f"Navigating to directory: {directory}")
            shell.send(f"cd {directory}\n")
            time.sleep(3)
            output = shell.recv(1024).decode("utf-8")
            logging.debug(f"Received output: {output}")
            """
            # Confirm directory with pwd
            shell.send("pwd\n")
            time.sleep(3)
            if shell.recv_ready():
                output = shell.recv(4096).decode("utf-8")
                logging.info(f"Output after navigating to directory: {output}")
                if directory not in output:
                    raise ValueError(f"Failed to navigate to directory: {directory}")
                else:
                    logging.info(f"Successfully navigated to {directory}")
             """   
    except Exception as e:
        logging.error(f"Error during interactive login or navigation: {e}")
        raise


def connect_to_unix_server(config_path, environment, store_number):
    """
    Connects to the UNIX server, triggers the batch job, and keeps the connection open.

    Args:
        config (dict): Configuration loaded from config.json.
        environment (str): Environment key (e.g., sys1, sys2).
        store_number (str): Store number to be passed to the batch job.

    Returns:
        tuple: (str, paramiko.SSHClient, paramiko.Channel)
               Result of the batch job, SSH client, and active shell channel.
    """
    config = load_config(config_path)
    if not config:
        return None

    module_config = config["modules"].get("move_to_fill", {})
    """
    try:
        validate_config(module_config, environment)
    except ValueError as e:
        logging.error(f"Configuration validation error: {e}")
        return None
    """
    env_config = module_config.get("environments", {}).get(environment, {})
    hostname = env_config.get("hostname")
    directory = env_config.get("directory")
    username = module_config.get("username")

    password = fetch_value_from_url(config_path)

    #logging.info(f"Fetched password: {password}")

    if not password:
        logging.error("Failed to retrieve password for UNIX connection")
        return None

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        logging.debug(f"Connecting to UNIX server {hostname} as {username}...")
        ssh.connect(hostname=hostname, username=username, password=password)

        # Open an interactive shell
        shell = ssh.invoke_shell()
        logging.info("Interactive shell opened.")

        # Handle interactive login process
        handle_interactive_login(shell, environment, directory)

         # Trigger the batch job
        result = trigger_batch_job(shell, store_number)
        logging.debug(f"Batch job result: {result}")

        return result, ssh, shell   # Return the shell for further interactions
    except paramiko.AuthenticationException:
        logging.error("Authentication failed while connecting to UNIX server")
    except paramiko.SSHException as e:
        logging.error(f"SSH error occurred: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    #return None

def trigger_batch_job(shell, store_number):
    """
    Triggers the interactive batch job and extracts the result.
    """
    logging.info("Entered trigger_batch_job function.")
    try:
        # Step 1: Send "move_to_fill"
        shell.send("move_to_fill\n")
        logging.debug("Sent 'move_to_fill' command.")
        time.sleep(2)
        output = shell.recv(1024).decode("utf-8")
        logging.debug(f"Received output: {output}")

        # Step 2: Check for "Please enter store number"
        if "Please enter store number" in output:
            shell.send(f"{store_number}\n")
            logging.debug(f"Sent store number: {store_number}")
            time.sleep(2)
            output = shell.recv(1024).decode("utf-8")
            logging.debug(f"Received output: {output}")

        # Step 3: Check for "Is this correct"
        if "Is this correct" in output:
            shell.send("y\n")
            logging.debug("Sent 'y' for confirmation.")
            time.sleep(2)
            output = shell.recv(1024).decode("utf-8")
            logging.debug(f"Received output: {output}")

        # Step 4: Check for "Would you like to use the default values" 
        if "Would you like to use the default values" in output:
            shell.send("y\n")
            logging.debug("Sent 'y' for confirmation.")
            time.sleep(2)
            output = shell.recv(4096).decode("utf-8")
            logging.debug(f"Received output: {output}")

        # Step 8: Wait until the job runs and "Done!" is displayed
        output = wait_for_prompt(shell, "Done!")
        logging.debug(f"Final batch job output: {output}")
        if "Done!" not in output:
            logging.error("Expected 'Done!' not found in batch job output.")
            raise ValueError("Batch job did not complete successfully.")
        else:
            logging.info("Batch job completed successfully.")

        # Step 9: Extract the dynamic result message
        result_line = extract_result_line(output, ["There was", "There were"], "moved into the tbf0_fill table")
        if not result_line:
            logging.error("Failed to parse the result line for UI.")
            raise ValueError("Failed to parse the result line for UI.")
        logging.info(f"Batch job result: {result_line}")

        return result_line  # Return the result for display in the UI
    
    except Exception as e:
        logging.error(f"Error during batch job: {e}")
        raise
    finally:
        # Step 10: Close the shell session
        pass

def wait_for_prompt(shell, expected_prompt, timeout=90):
    """
    Waits for a specific prompt in the shell output within a timeout.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if shell.recv_ready():
            output = shell.recv(4096).decode("utf-8")
            if expected_prompt in output:
                return output
        time.sleep(1)  # Check every second
    return None

def extract_result_line(output, prefixes, suffix):
    """
    Extracts a specific line containing dynamic values from the output.
    """
    for prefix in prefixes:
        # Adjust suffix to match "record" or "records"
        pattern = rf"{prefix} (\d+) record(?:s)? {suffix}"
        match = re.search(pattern, output)
        if match:
            return match.group(0)  # Return the full matched line
    return None

def verify_rx_in_fill_table_via_sqlplus(shell, config, rx_details, store_number):
    """
    Verifies RX details in the database using SQL*Plus via the active shell connection.

    Args:
        shell (paramiko.Channel): Active shell channel from the UNIX server connection.
        config (dict): Configuration loaded from config.json.
        rx_details (list[dict]): List of RX details (rx_nbr, fill_nbr, fill_dsp).
        store_number (str): Store number for the database query.

    Returns:
        list: Messages for the UI.
        dict: Query results for use in the next step.
    """
    db_config = config["modules"]["db"]["environments"]["sys1"]  # Adjust for dynamic environments if needed
    username = db_config["username"]
    password = db_config["password"]

    messages = []
    query_results = []

    try:
        # Start SQL*Plus session
        shell.send("sqlplus\n")
        time.sleep(2)

        # Provide username and password
        shell.send(f"{username}\n")
        time.sleep(2)
        shell.send(f"{password}\n")
        time.sleep(3)

        for rx in rx_details:
            query = (
                f"SELECT COUNT(*) FROM TBF0_FILL WHERE STORE_NBR = {store_number} "
                f"AND RX_NBR = {rx['rx_nbr']} AND FILL_NBR = {rx['fill_nbr']} "
                f"AND FILL_NBR_DISPENSED = {rx['fill_dsp']};"
            )
            shell.send(f"{query}\n")
            time.sleep(2)

            # Capture the query result
            if shell.recv_ready():
                output = shell.recv(4096).decode("utf-8")
                logging.debug(f"Query result for RX {rx['rx_nbr']}: {output}")

                # Parse the SQL result
                if "COUNT(*)" in output:
                    match = re.search(r"COUNT\(\*\)\s*\n*-*\n*\s*(\d+)", output, re.MULTILINE)
                    if match:
                        count = int(match.group(1))
                        if count > 0:
                            logging.info(f"✅ RX {rx['rx_nbr']} is found in Fill table. Adding for processing.")
                            message = f"Rx {rx['rx_nbr']} is moved to fill table."
                            query_results.append({
                                "rx_nbr": rx["rx_nbr"],
                                "fill_nbr": rx["fill_nbr"],
                                "fill_dsp": rx["fill_dsp"],
                                "store_nbr": store_number,
                                "found": True
                            })
                            messages.append(message)  # Only add success message when count > 0
                        else:
                            message = f"Rx {rx['rx_nbr']} is NOT found in the fill table."
                            query_results.append({
                                "rx_nbr": rx["rx_nbr"],
                                "fill_nbr": rx["fill_nbr"],
                                "fill_dsp": rx["fill_dsp"],
                                "store_nbr": store_number,
                                "found": False
                            })
                            messages.append(message)  # Only add failure message when count = 0
                    else:
                        logging.error("Failed to parse the COUNT(*) result from the SQL output.")

        # Exit SQL*Plus session
        shell.send("exit;\n")
        time.sleep(2)

    except Exception as e:
        logging.error(f"Error during database verification: {e}")
        raise

    return messages, query_results

def save_pdf(rx_nbr, fill_nbr):
    """
    Locate and rename the downloaded PDF file.
    """

    save_directory = r"C:\Tools\ABOP"
    default_filename = os.path.join(save_directory, "RxAuditPDFReportRH.pdf")
    new_filename = os.path.join(save_directory, f"RxAuditPDFReportRH_{rx_nbr}_{fill_nbr}.pdf")

    logging.info("Waiting for the PDF to finish downloading...")

    # Wait up to 15 seconds for the file to appear
    timeout = 15
    start_time = time.time()

    while not os.path.exists(default_filename):
        if time.time() - start_time > timeout:
            logging.error("❌ PDF file did not appear in the expected location.")
            return
        time.sleep(1)

    logging.info(f"✅ Found PDF: {default_filename}")

    # Rename the file
    try:
        os.rename(default_filename, new_filename)
        logging.info(f"✅ Renamed PDF to: {new_filename}")
    except Exception as e:
        logging.error(f"❌ Failed to rename PDF: {e}")

    # Cleanup: Delete generic PDFs and files older than 10 days
    try:
        ten_days_ago = datetime.now() - timedelta(days=10)

        for file in os.listdir(save_directory):
            file_path = os.path.join(save_directory, file)

            # Remove only generic "RxAuditPDFReportRH.pdf" or files older than 10 days
            if (file == "RxAuditPDFReportRH.pdf") or \
               (file.endswith(".pdf") and os.path.getmtime(file_path) < ten_days_ago.timestamp()):

                os.remove(file_path)
                logging.info(f"🗑 Deleted old/generic file: {file_path}")

    except Exception as e:
        logging.error(f"❌ Failed to clean up old PDFs: {e}")

def initialize_driver():
    options = webdriver.EdgeOptions()

    # ✅ Ignore SSL and security warnings
    options.add_argument("--headless=new") 
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")  # Ensure full viewport capture
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")

    # ✅ Configure Edge to prevent automatic PDF downloads
    prefs = {
        "download.default_directory": r"C:\Tools\ABOP",  # Set desired save path
        "plugins.always_open_pdf_externally": True,  # ✅ Open PDF in browser (no auto-download)
        "download.prompt_for_download": False,  # ✅ Force Save As prompt
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.default_content_setting_values.popups": 0,  # Disable popups
        "safebrowsing.enabled": False  # Disable security warnings
    }
    options.add_experimental_option("prefs", prefs)

    # Enable logging and debugging capabilities
    options.set_capability("ms:loggingPrefs", {"performance": "ALL"})

    # ✅ Launch Edge with modified settings
    driver = webdriver.Edge(options=options)
    return driver

def process_rx_audit_backend(config, environment, store_number, rx_nbr, fill_nbr):
    """
    Launch RX Audit App, log in, navigate to the next page, select the correct RX hyperlink, and download the PDF.
    """
    rx_audit_config = config["modules"]["rx_audit_app"]
    url = rx_audit_config["environments"][environment]["url"]
    username = rx_audit_config["username"]
    password = rx_audit_config["password"]

    logging.info(f"Launching RX Audit App at {url}")

    logging.info("Initializing Edge WebDriver...")
    driver = initialize_driver()  # Use the modified Edge WebDriver setup
    driver.get(url)

    try:
        logging.info("Waiting for the page to load...")

        # ✅ **Wait until login form loads**
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "userid"))
        )

        # ✅ **Enter login details**
        driver.find_element(By.NAME, "userid").send_keys(username)
        driver.find_element(By.NAME, "password").send_keys(password)

        # ✅ **Click Login button**
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()

        logging.info("Successfully logged into RX Audit App.")
        
        # ✅ **Wait for the RX Audit Form**
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "textRxNbr"))
        )

        # ✅ **Identify and fill Store Number and Rx Number**
        store_number_field = driver.find_element(By.NAME, "textStoreNbr")
        rx_number_field = driver.find_element(By.NAME, "textRxNbr")

        store_number_field.clear()
        rx_number_field.clear()

        expected_link_text = f"{rx_nbr}-{fill_nbr}"

        store_number_field.send_keys(store_number)
        rx_number_field.send_keys(rx_nbr)

        logging.info(f"Entered Store Number and Rx Number: {rx_nbr}")

        # ✅ **Submit the form**
        next_button = driver.find_element(By.XPATH, "//input[@value='Next >>']")
        next_button.click()

        logging.info("Submitted RX Audit form successfully.")

        
        # ✅ **Wait for hyperlink to be available**
        rx_link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.LINK_TEXT, expected_link_text))
        )

        if not rx_link:
            logging.error(f"Failed to find the RX hyperlink: {expected_link_text}")
            return

        logging.info(f"Found the RX hyperlink: {expected_link_text}")

        # ✅ **Ensure `C:\Tools\ABOP` exists before saving**
        save_directory = r"C:\Tools\ABOP"
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
            logging.info(f"✅ Created directory: {save_directory}")

        # ✅ **Click on the link to open the PDF page**
        main_window = driver.current_window_handle
        rx_link.click()
        time.sleep(5)  # Wait for navigation to complete

         # ✅ **Switch to the new window**
        new_window = [window for window in driver.window_handles if window != main_window][0]
        driver.switch_to.window(new_window)
        logging.info("Switched to the new window containing the PDF.")

        # ✅ **Save the PDF by clicking the save button**
        save_pdf(rx_nbr, fill_nbr)

        # ✅ **Close the new window and switch back to the main window**
        #driver.close()
        driver.switch_to.window(main_window)
        logging.info("Switched back to the main window.")

        return True  # ✅ Return success

    except Exception as e:
        logging.error(f"Error during RX Audit process: {e}")
        return False  # Return failure

    finally:
        logging.info("Closing browser session.")
        driver.quit()  # ✅ Close the browser properly

# Example usage
if __name__ == "__main__":
    CONFIG_PATH = "./config/config.json"  # Path to config.json
    ENVIRONMENT = "sys1"
    STORE_NUMBER = "59148"
    RX_DETAILS = [
        {"rx_nbr": "120442", "fill_nbr": "1", "fill_dsp": "1"},
        {"rx_nbr": "120429", "fill_nbr": "1", "fill_dsp": "1"},
        {"rx_nbr": "120431", "fill_nbr": "1", "fill_dsp": "1"} 
    ]

    config = load_config(CONFIG_PATH) 

    try:

        # ✅ Step 1: Execute Sell Service
        logging.info("Starting Step 1: Sell Service.")
        sell_service_response = perform_sell_service(ENVIRONMENT, STORE_NUMBER, RX_DETAILS)
        for rx_id, result in sell_service_response.items():  # Updated 'sell_results' to 'sell_service_response'
            logging.info(f"{rx_id}: {result}")

         # ✅ Step 2: Connect to UNIX Server and Trigger Batch Job
        logging.info("Starting Step 2: Trigger Batch Job.")
        batch_result, ssh_client, shell = connect_to_unix_server(CONFIG_PATH, ENVIRONMENT, STORE_NUMBER)
        if batch_result:
            logging.info(f"Result for UI: {batch_result}")
        else:
            logging.error("Batch job execution failed.")

        # ✅ Step 3: Verify RX details in the database
        logging.info("Starting Step 3: Verify Data in Fill Table.")
        step3_messages, step3_results = verify_rx_in_fill_table_via_sqlplus(shell, config, RX_DETAILS, STORE_NUMBER)

        # Display messages for UI from Step 3
        for message in step3_messages:
            logging.info(message)

        # Save or process step3_results for future steps
        logging.info("Step 3 completed successfully.")

        # Filter RX details where `found` is True
        found_rx_details = [
            rx for rx in step3_results if rx.get("found") is True
        ]   

        
        # ✅ Step 4: Run RX Audit for each found RX
        processed_rx_set = set()

        if found_rx_details:
            logging.info("Starting Step 4: RX Audit App Login and PDF Generation.")
    
            for idx, rx in enumerate(found_rx_details, start=1):
                rx_nbr = rx["rx_nbr"]
                fill_nbr = rx["fill_nbr"]

                # Skip duplicates
                if (rx_nbr, fill_nbr) in processed_rx_set:
                    logging.warning(f"Skipping duplicate RX: {rx_nbr}-{fill_nbr}")
                    continue

                logging.info(f"Processing RX {idx}/{len(found_rx_details)}: {rx_nbr}-{fill_nbr}")

                logging.debug(f"Calling process_rx_audit_backend with RX {rx_nbr} - Fill {fill_nbr}")
                success = process_rx_audit_backend(config, ENVIRONMENT, STORE_NUMBER, rx_nbr, fill_nbr)

                if not success:
                    logging.error(f"Failed processing RX Audit for Rx: {rx_nbr}-{fill_nbr}")

                # Mark RX as processed
                processed_rx_set.add((rx_nbr, fill_nbr))

        else:
            logging.info("No valid RXs found for RX Audit process.")
       
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")

    finally:
        if 'ssh_client' in locals() and ssh_client:
            ssh_client.close()
            logging.info("SSH connection closed.")