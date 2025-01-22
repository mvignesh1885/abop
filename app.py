import paramiko
import json
import requests
from bs4 import BeautifulSoup
import logging
import urllib3  # Import urllib3 for disabling warnings
import time
import re

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

                # Parse the result
                if "1" in output:  # Check for a valid entry
                    message = f"Rx {rx['rx_nbr']} is moved to fill table."
                    messages.append(message)
                    query_results.append({
                        "rx_nbr": rx['rx_nbr'],
                        "fill_nbr": rx['fill_nbr'],
                        "fill_dsp": rx['fill_dsp'],
                        "store_nbr": store_number,
                        "found": True
                    })
                else:
                    message = f"Rx {rx['rx_nbr']} is NOT found in the fill table."
                    messages.append(message)
                    query_results.append({
                        "rx_nbr": rx['rx_nbr'],
                        "fill_nbr": rx['fill_nbr'],
                        "fill_dsp": rx['fill_dsp'],
                        "store_nbr": store_number,
                        "found": False
                    })

        # Exit SQL*Plus session
        shell.send("exit;\n")
        time.sleep(2)

    except Exception as e:
        logging.error(f"Error during database verification: {e}")
        raise

    return messages, query_results


# Example usage
if __name__ == "__main__":
    CONFIG_PATH = "./config/config.json"  # Path to config.json
    ENVIRONMENT = "sys1"
    STORE_NUMBER = "59403"
    RX_DETAILS = [
        {"rx_nbr": "4614694", "fill_nbr": "1", "fill_dsp": "1"},
        {"rx_nbr": "4614693", "fill_nbr": "1", "fill_dsp": "1"}  
    ]

    config = load_config(CONFIG_PATH) 

    try:

        # Step 1: Execute Sell Service
        logging.info("Starting Step 1: Sell Service.")
        sell_service_response = perform_sell_service(ENVIRONMENT, STORE_NUMBER, RX_DETAILS)
        for rx_id, result in sell_service_response.items():  # Updated 'sell_results' to 'sell_service_response'
            logging.info(f"{rx_id}: {result}")

        # Step 2: Connect to UNIX Server and Trigger Batch Job
        logging.info("Starting Step 2: Trigger Batch Job.")
        batch_result, ssh_client, shell = connect_to_unix_server(CONFIG_PATH, ENVIRONMENT, STORE_NUMBER)
        if batch_result:
            logging.info(f"Result for UI: {batch_result}")
        else:
            logging.error("Batch job execution failed.")

        # Step 3: Verify RX details in the database
        logging.info("Starting Step 3: Verify Data in Fill Table.")
        step3_messages, step3_results = verify_rx_in_fill_table_via_sqlplus(shell, config, RX_DETAILS, STORE_NUMBER)

        # Display messages for UI from Step 3
        for message in step3_messages:
            logging.info(message)

        # Save or process step3_results for future steps
        logging.info("Step 3 completed successfully.")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        # Close the SSH connection
        if 'ssh_client' in locals() and ssh_client:
            ssh_client.close()
            logging.info("SSH connection closed.")

#check batch result extraction logic