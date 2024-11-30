import argparse
import logging
import requests
from utils.config import Config
from utils.worker import IndexerProcessorServer
from utils.logging import JsonFormatter, CustomLogger
import os 
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()



def fetch_latest_version():
    url = "https://api.aptoscan.com/v1/transactions?cluster=mainnet&page=1&type=user_transaction"
    
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        # print(data)
        if "data" in data and data["data"]:
            latest_version = data["data"]['list_trans'][0]["trans_version"]
            return latest_version
        else:
            logging.error("No transaction data found in API response.")
            return None
    else:
        logging.error(f"Failed to fetch latest version, status code: {response.status_code}")
        return None

if __name__ == "__main__":
    # Configure the logger
    logger = CustomLogger("default_python_logger")
    logger.setLevel(logging.INFO)

    # Create a stream handler for stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(JsonFormatter())

    # Add the stream handler to the logger
    logger.addHandler(stream_handler)
    logging.root = logger

    # Argument parser for config file
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Path to config file", required=True)
    args = parser.parse_args()

    # Load the config
    config = Config.from_yaml_file(args.config)
    # Fetch the latest transaction version
    latest_version = fetch_latest_version()
    if latest_version is not None:
        # Update the config with the latest version
        config.server_config.starting_version = latest_version
        logger.info(f"Updated starting_version to {latest_version}")
    config.server_config.postgres_connection_string=os.getenv("DB_STRING")  # type: ignore
    config.server_config.auth_token=os.getenv("AUTH_TOKEN")  # type: ignore


    # Initialize and run the indexer server
    indexer_server = IndexerProcessorServer(config)
    indexer_server.run()
