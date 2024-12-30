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

# Load the configuration from config.json
def load_config(config_path):
    try:
        with open(config_path, 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from config file: {e}")
        return None

# Validate config file loading         
def validate_config(module_config, environment):
    """
    Validates the configuration for the given module and environment.
    """
    if "environments" not in module_config:
        raise ValueError("Environments key is missing in module configuration")
    if environment not in module_config["environments"]:
        raise ValueError(f"Environment '{environment}' not found in module configuration")
    if "username" not in module_config:
        raise ValueError("Username is missing in module configuration")


# Fetch password from URL using username from config.json
def fetch_value_from_url(config_path):
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

# Interactive login
def handle_interactive_login(shell, environment):
    """
    Handles the interactive login process by monitoring the output and sending the correct responses
    based on keywords for Sys1 and Sys2 environments.
    """
    try:
        while True:
            if shell.recv_ready():
                output = shell.recv(1024).decode("utf-8")
                logging.info(f"Received output: {output}")

                # Handle Sys1 specific keywords
                if environment == "sys1":
                    if "ASM" in output:
                        shell.send("N\n")
                        logging.info("Sent 'N' for Sys1 ASM-related question.")
                    elif "tstdb01" in output:
                        shell.send("Y\n")
                        logging.info("Sent 'Y' for Sys1 target question.")

                # Handle Sys2 specific keywords
                elif environment == "sys2":
                    if "agent12c" in output or "ASM" in output:
                        shell.send("N\n")
                        logging.info("Sent 'N' for Sys2 agent12c or ASM-related question.")
                    elif "thcicp01" in output:
                        shell.send("Y\n")
                        logging.info("Sent 'Y' for Sys2 target question.")

                # Check for successful login prompt
                if (environment == "sys1" and "ticpdb2" in output) or (environment == "sys2" and "thcicp01" in output):
                    logging.info("Interactive login complete.")
                    break

                # Check for errors
                if "Password locked" in output or "Access denied" in output:
                    raise ValueError("Login failed due to locked password or access issue.")

                time.sleep(1)  # Wait briefly before checking output again
    except Exception as e:
        logging.error(f"Error during interactive login: {e}")
        raise


# Connect to UNIX server
def connect_to_unix_server(config_path, environment):
    config = load_config(config_path)
    if not config:
        return None

    module_config = config["modules"].get("move_to_fill", {})
    
    try:
        validate_config(module_config, environment)
    except ValueError as e:
        logging.error(f"Configuration validation error: {e}")
        return None

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
        logging.info(f"Connecting to UNIX server {hostname} as {username}...")
        ssh.connect(hostname=hostname, username=username, password=password)

        # Open an interactive shell
        shell = ssh.invoke_shell()
        logging.info("Interactive shell opened.")

        # Handle interactive login process
        handle_interactive_login(shell, environment)

        # Navigate to the directory if specified
        if directory:
            logging.info(f"Navigating to directory: {directory}")
            shell.send(f"cd {directory}\n")
            time.sleep(1)  # Wait for command execution

        return shell  # Return the shell for further interactions
    except paramiko.AuthenticationException:
        logging.error("Authentication failed while connecting to UNIX server")
    except paramiko.SSHException as e:
        logging.error(f"SSH error occurred: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        ssh.close()

    return None

# Example usage
if __name__ == "__main__":
    CONFIG_PATH = "./config/config.json"  # Path to config.json
    ENVIRONMENT = "sys2"

    # Connect to the UNIX server
    ssh_client = connect_to_unix_server(CONFIG_PATH, ENVIRONMENT)
    if ssh_client:
        try:
            logging.info("Perform further operations with the SSH client here.")
        finally:
            logging.info("Closing the connection to the server.")
            ssh_client.close()
    else:
        logging.error("Failed to connect to UNIX server.")

# For Sys 2 also use the same host name to get oper pwd