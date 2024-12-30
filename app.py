import paramiko
import json
import requests
from bs4 import BeautifulSoup
import logging
import urllib3  # Import urllib3 for disabling warnings
import time

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
"""    
def validate_config(module_config, environment):
    if "environments" not in module_config:
        raise ValueError("Environments key is missing in module configuration")
    if environment not in module_config["environments"]:
        raise ValueError(f"Environment '{environment}' not found in module configuration")
    if "username" not in module_config:
        raise ValueError("Username is missing in module configuration")
""" 
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
                        time.sleep(5)
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
                        time.sleep(5)
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
    Connect to UNIX server
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

        return result   # Return the shell for further interactions
    except paramiko.AuthenticationException:
        logging.error("Authentication failed while connecting to UNIX server")
    except paramiko.SSHException as e:
        logging.error(f"SSH error occurred: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
    finally:
        logging.info("Closing the SSH connection.")
        ssh.close()
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
            logging.info(f"Received output: {output}")

        # Step 8: Wait until the job runs and "Done!" is displayed
        output = wait_for_prompt(shell, "Done!")
        if not output:
            raise ValueError("Job did not complete successfully.")
        logging.info("Batch job completed successfully.")

        # Step 9: Extract the dynamic result message
        result_line = extract_result_line(output, "There were", "records moved into the tbf0_fill table")
        logging.debug(f"Batch job result: {result_line}")

        return result_line  # Return the result for display in the UI
    
    except Exception as e:
        logging.error(f"Error during batch job: {e}")
        raise
    finally:
        # Step 10: Close the shell session
        shell.close()
        logging.debug("Shell session closed.")

def wait_for_prompt(shell, expected_prompt, timeout=30):
    """
    Waits for a specific prompt in the shell output within a timeout.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        if shell.recv_ready():
            output = shell.recv(1024).decode("utf-8")
            if expected_prompt in output:
                return output
        time.sleep(1)  # Check every second
    return None

def extract_result_line(output, start_text, end_text):
    """
    Extracts a specific line containing dynamic values from the output.
    """
    try:
        start_idx = output.find(start_text)
        if start_idx == -1:
            return None
        end_idx = output.find(end_text, start_idx)
        if end_idx == -1:
            return None
        return output[start_idx:end_idx + len(end_text)].strip()
    except Exception as e:
        logging.error(f"Error extracting result line: {e}")
        return None


# Example usage
if __name__ == "__main__":
    CONFIG_PATH = "./config/config.json"  # Path to config.json
    ENVIRONMENT = "sys1"
    STORE_NUMBER = "59163"

    try:
        # Connect to the UNIX server
        result  = connect_to_unix_server(CONFIG_PATH, ENVIRONMENT, STORE_NUMBER)
        if result:
            logging.info(f"Result for UI: {result}")
        else:
            logging.error("Batch job execution failed.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
