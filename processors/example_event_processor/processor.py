from aptos_protos.aptos.transaction.v1 import transaction_pb2
from processors.example_event_processor.models import Event
from typing import List
from utils.transactions_processor import ProcessingResult
from utils import general_utils
from utils.transactions_processor import TransactionsProcessor
from utils.models.schema_names import EXAMPLE
from utils.session import Session
from utils.processor_name import ProcessorName
from scripts.price import get_price
from time import perf_counter
from processors.example_event_processor.helpers import escaped_string_to_hex
import json
import pandas as pd
import subprocess
from dotenv import load_dotenv
import psycopg2 , os
import time
import requests
from constants import COINS, PROTOCOLS
import logging
from psycopg2.extras import execute_values
from functools import lru_cache

load_dotenv()

# Access environment variables
DB_STRING = os.getenv("DB_STRING")


# Configure logger
logging.basicConfig(
    level=logging.DEBUG,  # Set the minimum level of messages to capture
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("example_event_processor.log"),  # Log to a file
        logging.StreamHandler()  # Also log to console
    ]
)


# ===================== HELPER FXNS ==========================================================
# def price_liquidswap(coin,amount):
#     division_factor=10**6
#     try:
#         if coin == "0xdd89c0e695df0692205912fb69fc290418bed0dbe6e4573d744a6d5e6bab6c13::coin::T":
#             logging.info("Coin is sol so changing amount to 100000")
#             amount = 1000
#             division_factor=10
#         res=subprocess.run("pwd", shell=True, capture_output=True, text=True)
#         logging.info(res.stdout)
#         # Define the command to be executed
#         logging.info(coin)
#         command = f'node scripts/liquidswap_router.mjs "{coin}" "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC" {amount}'
#         logging.info(command)
#         # Execute the command
#         result = subprocess.run(command, shell=True, capture_output=True, text=True)
#         logging.info(result)
#         # Check if the command was successful
#         if result.returncode == 0:
#             # Parse and return the price from the output
#             return (int(result.stdout.strip()))/division_factor
#         else:
#             # Print the error and return None
#             logging.info(f"Error executing command: {result.stderr}")
#             return None
#     except Exception as e:
#         logging.info(f"Exception occurred: {e}")
#         return None

# def get_price(coin_address: str, amount,provider= None) -> float:
#     # Set up endpoint, API key, and headers
#     end_point = "https://api.panora.exchange/prices"
#     api_key = "a4^KV_EaTf4MW#ZdvgGKX#HUD^3IFEAOV_kzpIE^3BQGA8pDnrkT7JcIy#HNlLGi"
#     headers = {
#         "x-api-key": api_key,
#     }
    
#     # Configure query parameters
#     query = {
#         "tokenAddress": coin_address,
#     }
    
#     # Make the API request
#     try:
#         response = requests.get(end_point, headers=headers, params=query)
#         response.raise_for_status()  # Raise an error for bad responses
#         data = response.json()[0]
        
#         # Return the USD price if it exists in the response
#         usd_price = data.get("usdPrice")
#         if usd_price:
#             return float(usd_price)
#         else:
#             raise ValueError("USD price not found in the response.")
    
#     except requests.exceptions.RequestException as e:
#         logging.info("API request failed:", e)
#         return 0.0
 
# def price_thalaswap(coin):
#     try:
#         # Define the command to be executed
#         command = f'node scripts/thalaswap_router.mjs "{coin}" "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC" {1}'
#         logging.info(command)
#         # Execute the command
#         result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
#         # Check if the command was successful
#         if result.returncode == 0:
#             amt = float(result.stdout.strip())
#             logging.info(amt)
#             return amt
#         else:
#             # Print the error and return None
#             logging.info(f"Error executing command: {result.stderr}")
#             return None
#     except Exception as e:
#         logging.info(f"Exception occurred: {e}")
#         return None
    
def extract_coins(type_str):
    coin_list = type_str.split('<')[1].split('>')[0]
    coins = [coin.strip() for coin in coin_list.split(',')]
    return coins[0], coins[1]

class DatabaseManager:
    def __init__(self, db_string):
        self.db_string = db_string
        self.connection = None

    def __enter__(self):
        self.connection = psycopg2.connect(self.db_string)
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
            self.connection.close()

class PriceCache:
    def __init__(self, cache_duration=300):  # 5 minutes cache duration
        self.cache = {}
        self.cache_duration = cache_duration
        self.last_update = {}
    
    def get(self, coin_address):
        current_time = time.time()
        if coin_address in self.cache:
            if current_time - self.last_update[coin_address] < self.cache_duration:
                return self.cache[coin_address]
        return None
    def set(self, coin_address, price):
        self.cache[coin_address] = price
        self.last_update[coin_address] = time.time()
#============================== CONSTANTS ============================================
def calculate_slippage(delta_x, delta_y, price_x, price_y):
    try:
        if price_y == 0 or delta_x == 0:
            return 0.0
            
        delta_y_expected = (delta_x * price_x) / price_y
        if delta_y_expected == 0:
            return 0.0
            
        slippage = ((delta_y_expected - delta_y) / delta_y_expected) * 100
        return round(slippage, 2)
    except Exception as e:
        logging.error(f"Error calculating slippage: {e}")
        return 0.0
#============================== CONSTANTS ============================================

@lru_cache(maxsize=1000)
def get_div_factor(coin_address, file_path='Coins.json'):
    """
    Get the division factor for the given coin based on its decimal value.
    If the coin is not found in the JSON, fetch its metadata from the API,
    update the JSON, and save it.
    
    Args:
        coin_address (str): The address of the coin in the format '<address>::<module>::<coin>'.
        file_path (str): Path to the JSON file for updating if needed.
        
    Returns:
        float: Division factor (10 * float(decimals)).
    """
    # Load the JSON data
    with open(file_path, 'r') as f:
        coin_data = json.load(f)

    # Check if the coin exists in the JSON
    for coin in coin_data:
        if coin['token_type']['type'] == coin_address:
            decimals = coin.get('decimals')
            symbol = coin.get('symbol', 'Unkown')
            return symbol,10 ** float(decimals)
    
    # If coin not found, fetch from API
    # Split the coin address into parts: <address>::<module>::<coin>
    address, module, coin_type = coin_address.split('::')
    rpc_url = os.environ.get('RPC_URL', 'https://fullnode.mainnet.aptoslabs.com/v1')


    # Construct the URL using the address and token type
    url = f"{rpc_url}/accounts/{address}/resource/0x1::coin::CoinInfo%3C{address}::{module}::{coin_type}%3E"
    logging.info(url)
    
    response = requests.get(url)

    if response.status_code == 200:
        # Parse the response JSON
        coin_metadata = response.json().get('data', {})
        decimals = coin_metadata.get('decimals', 6)  # Default to 6 if decimals not found
        name = coin_metadata.get('name', '')
        symbol = coin_metadata.get('symbol', '')

        # Construct new coin data
        new_coin_entry = {
            'name': name,
            'symbol': symbol,
            'decimals': decimals,
            'token_type': {
                'type': coin_address
            }
        }
        logging.info(new_coin_entry)
        # Add the new entry to the JSON
        coin_data.append(new_coin_entry)

        # Save the updated JSON data
        with open(file_path, 'w') as f:
            json.dump(coin_data, f, indent=4)

        return symbol, 10 ** float(decimals)

    else:
        return "Unknown",10 ** 6  # Return default division factor if API fails

# Constants
COINS_FILE_PATH = 'Coins.json'  # Path to your coins JSON file
USDC_ADDRESS = "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"

# Protocol constants
THALASWAP = PROTOCOLS['THALASWAP']
LIQUIDSWAP = PROTOCOLS['LIQUIDSWAP']
PANCAKE = PROTOCOLS['PANCAKE']
SUSHISWAP = PROTOCOLS['SUSHISWAP']

# Print protocol constants for debugging
# logging.info(f"Protocols: THALASWAP={THALASWAP}, LIQUIDSWAP={LIQUIDSWAP}, PANCAKE={PANCAKE}")


#==================================================================================================
class ExampleEventProcessor(TransactionsProcessor):
    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.price_cache = PriceCache(cache_duration=300)
    def name(self) -> str:
        return ProcessorName.EXAMPLE_EVENT_PROCESSOR.value

    def schema(self) -> str:
        return EXAMPLE
    
    def fetch_token_prices(self,coin1, coin2, provider, div_factor1, div_factor2):
        def get_cached_price(coin, div_factor):
            # Use cached price if available
            price = self.price_cache.get(coin)
            if price is None:
                price = get_price(coin, amount=div_factor, provider=provider)
                self.price_cache.set(coin, price)
            return price

        if coin1 == USDC_ADDRESS:
            price_x = 1
            price_y = get_cached_price(coin2, div_factor2)
        elif coin2 == USDC_ADDRESS:
            price_y = 1
            price_x = get_cached_price(coin1, div_factor1)
        else:
            price_x = get_cached_price(coin1, div_factor1)
            price_y = get_cached_price(coin2, div_factor2)

        return price_x, price_y
    
    def calculate_tvl(self,coin_x_reserve, coin_y_reserve, provider, change_type):
        # Common logic for calculating TVL
        try:
            # Extract coin types based on change_type
            coin1, coin2 = extract_coins(change_type)

            # Determine the division factors based on the coin types
            symbol1, div_factor1 = get_div_factor(coin1)
            symbol2,div_factor2 = get_div_factor(coin2)

            # Convert reserves to float
            coin_x_reserve = coin_x_reserve / div_factor1
            coin_y_reserve = coin_y_reserve / div_factor2
            
            # Fetch token prices
            price_x, price_y = self.fetch_token_prices(coin1, coin2, provider, div_factor1, div_factor2)

            # Calculate TVL if both prices are available
            tvl = 0
            if price_x and price_y:
                tvl = coin_x_reserve * price_x + coin_y_reserve * price_y
                return tvl
            else:
                self.logger.info(f"Error fetching prices for the tokens: {coin1}, {coin2}.")
                return 0


        except Exception as e:
            self.logger.info(f"Error processing TVL for {provider}: {e}")
            return 0 

    def process_transactions(
        self,
        transactions: list[transaction_pb2.Transaction],
        start_version: int,
        end_version: int,
    ) -> ProcessingResult:
        
        event_db_objs: List[Event] = []
        start_time = perf_counter()
        tvl_data = []
        pool_data={}
        for transaction in transactions:
            # self.logger.info(transaction)
            # Custom filtering
            # Here we filter out all transactions that are not of type TRANSACTION_TYPE_USER
            if transaction.type != transaction_pb2.Transaction.TRANSACTION_TYPE_USER:
                continue
            status=transaction.info.success
            if not status:
                continue
            
            changes=transaction.info.changes
            transaction_version = transaction.version
            transaction_block_height = transaction.block_height
            transaction_timestamp = general_utils.parse_pb_timestamp(transaction.timestamp)
            user_transaction = transaction.user
            aptos_price = self.fetch_token_prices("0x1::aptos_coin::AptosCoin", USDC_ADDRESS, "LIQUIDSWAP", 6, 6)[0]

            fees=float((transaction.info.gas_used)/1000000)*aptos_price # type: ignore
            # self.logger.info("Processing events")
            valid_txn = False
            for event_index, event in enumerate(user_transaction.events):
                
                account_address = general_utils.standardize_address(event.key.account_address)
                creation_number = event.key.creation_number
                sequence_number = event.sequence_number
                type = event.type_str
                pool_id = type
                slippage=0
                Vol=0

                data = json.loads(str(event.data))
                
                provider = None
                price_x , price_y = None , None
                if "SwapEvent" in type:
                    try:
                        delta_x , delta_y = 0,0
                        coin1, coin2 = extract_coins(type)
                        symbol1, div_factor1 = get_div_factor(coin1)
                        symbol2,div_factor2 = get_div_factor(coin2)
                        pool_name=symbol1+"-"+symbol2
                        print(pool_name)
                        # self.logger.info(symbol1, symbol2)
                        # self.logger.info(div_factor1 , div_factor2)
                        decimal_x=None
                        # ========== LIQUIDSWAP VOLUME CALCULATION  =============================               
                        if account_address == LIQUIDSWAP:
                            valid_txn = True
                            provider = "LIQUIDSWAP"

                            pool_id = pool_id.replace("SwapEvent", "LiquidityPool")
                            data["x_in"] = int(data["x_in"]) / div_factor1
                            data["x_out"] = int(data["x_out"]) / div_factor1
                            data["y_out"] = int(data["y_out"]) / div_factor2  
                            data["y_in"] = int(data["y_in"]) / div_factor2  
                            # Calculate actual delta for X and Y
                            delta_x = abs(float(data["x_in"] - data["x_out"]))
                            delta_y= abs(float(data["y_in"] - data["y_out"]))

                         
                            price_x, price_y = self.fetch_token_prices(coin1, coin2, provider, div_factor1, div_factor2)
                            # Calculate slippage: (Expected Output - Actual Output) / Expected Output * 100%
                            slippage = calculate_slippage(delta_x, delta_y, price_x, price_y)
                            Vol = delta_x * price_x  # type: ignore
                            decimal_x=str(int(div_factor1)).count('0')

                            self.logger.info(f"Price of token X: {price_x}, Price of token Y: {price_y}, Delta X: {delta_x}, Delta Y: {delta_y}, Slippage: {slippage:.2f}%")


                        elif account_address == THALASWAP:
                            valid_txn = True
                            provider = "THALASWAP"

                            if "weighted_pool" in pool_id:
                                pool_id = pool_id.replace("SwapEvent", "WeightedPool")
                            else:
                                pool_id = pool_id.replace("SwapEvent", "StablePool")
                            
                            # Extract index values
                            index_of_amount_in = int(data['idx_in'])
                            index_of_amount_out = int(data['idx_out'])

                            # Check which coin is amount_in and which is amount_out based on indices
                            if index_of_amount_in == 0:
                                # Coin 1 is being traded in, Coin 2 is being traded out
                                delta_x = int(data['amount_in']) / div_factor1
                                delta_y = int(data['amount_out']) / div_factor2
                                price_x, price_y = self.fetch_token_prices(coin1, coin2, provider, div_factor1, div_factor2)
                                decimal_x=str(int(div_factor1)).count('0')

                            elif index_of_amount_in == 1:
                                # Coin 2 is being traded in, Coin 1 is being traded out
                                delta_x = int(data['amount_in']) / div_factor2
                                delta_y = int(data['amount_out']) / div_factor1
                                # Swap coin1 and coin2 because Coin 2 is being traded in
                                coin1, coin2 = coin2, coin1
                                price_x, price_y = self.fetch_token_prices(coin1, coin2, provider, div_factor1, div_factor2)
                                decimal_x=str(int(div_factor2)).count('0')

                            slippage = calculate_slippage(delta_x, delta_y, price_x, price_y)

                            # Log or self.logger.info the slippage with detailed price_x and price_y information
                            self.logger.info(f"Price of token X: {price_x}, Price of token Y: {price_y}, Delta X: {delta_x}, Delta Y: {delta_y} Slippage: {slippage:.2f}%")

                            Vol = delta_x * price_x  # type: ignore

                        elif account_address == PANCAKE:
                            valid_txn = True
                            provider = "PANCAKESWAP"
                            
                            pool_id = pool_id.replace("SwapEvent", "TokenPairReserve")
                            # Extract amount_x_in, amount_x_out, amount_y_in, and amount_y_out from data
                            delta_x = abs(int(data["amount_x_in"]) - int(data["amount_x_out"])) / div_factor1
                            delta_y = abs(int(data["amount_y_in"]) - int(data["amount_y_out"])) / div_factor2


                            price_x , price_y = self.fetch_token_prices(coin1, coin2, provider, div_factor1, div_factor2)

                            # Calculate slippage: (Expected Output - Actual Output) / Expected Output * 100
                            slippage = calculate_slippage(delta_x, delta_y, price_x, price_y)

                            # Log or self.logger.info the slippage
                            self.logger.info(f"Price of token X: {price_x}, Price of token Y: {price_y}, Delta X: {delta_x}, Delta Y: {delta_y}, Slippage: {slippage:.2f}%")
                            decimal_x=str(int(div_factor1)).count('0')
                            # Calculate volume
                            Vol = delta_x * price_x  # type: ignore
                        elif account_address == SUSHISWAP:
                            data=data.get("data")
                            
                            valid_txn = True
                            provider = "SUSHISWAP"
                            pool_id = pool_id.replace("SwapEvent", "TokenPairReserve")
                            # Extract amount_x_in, amount_x_out, amount_y_in, and amount_y_out from data
                            delta_x = abs(int(data["amount_x_in"]) - int(data["amount_x_out"])) / div_factor1
                            delta_y = abs(int(data["amount_y_in"]) - int(data["amount_y_out"])) / div_factor2
                            price_x, price_y = self.fetch_token_prices(coin1, coin2, provider, div_factor1, div_factor2)

                            slippage = calculate_slippage(delta_x, delta_y, price_x, price_y)

           
                            self.logger.info(f"Price of token X: {price_x}, Price of token Y: {price_y}, Delta X: {delta_x}, Delta Y: {delta_y}, Slippage: {slippage:.2f}%")
                            decimal_x=str(int(div_factor1)).count('0')
                            Vol = delta_x * price_x  # type: ignore

                        if provider:
                            if pool_id in pool_data:
                                pool_data[pool_id]["volume"] += Vol
                                pool_data[pool_id]["price"] = price_x
                            else:
                                pool_data[pool_id] = {
                                    "version": transaction_version,
                                    "pool_name": pool_name,
                                    "timestamp": transaction_timestamp,
                                    "pool_address": pool_id.replace(" ",""),
                                    "coin1": coin1,
                                    "coin2": coin2,
                                    "provider": provider,
                                    'slippage':slippage,
                                    "volume": Vol,
                                    "delta_x":delta_x,
                                    "price_x": price_x,
                                    "delta_y":delta_y,
                                    "price_y": price_y,
                                    'decimal_x':decimal_x,
                                    "fees": fees,
                                    "tvl": None,
                                }
                    except Exception as e:
                        self.logger.info(f"Unrecognized SwapEvent: {e}")
                        self.logger.info(f"Type: {type} Version {transaction_version}")
                # if type =="0x1::transaction_fee::FeeStatement":
                #     fees = int(data['total_charge_gas_units'])/1000000
                #     self.logger.info(transaction_hash , "Fees",fees)

# =============================================================================================================================
# =============================================================================================================================



            for change in changes:
                change_type = change.write_resource.type_str
                
                # Calculation of TVL for Liquidswap
                coin_x_reserve,coin_y_reserve=0,0
                coin1,coin2=None,None

                if "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::liquidity_pool::LiquidityPool" in change_type:
                    provider = "LIQUIDSWAP"
                    data = json.loads(change.write_resource.data)
                    coin_x_reserve = int(data['coin_x_reserve']['value'])
                    coin_y_reserve = int(data['coin_y_reserve']['value'])


                    tvl=self.calculate_tvl(coin_x_reserve, coin_y_reserve,provider,change_type)
                    if change_type in pool_data:
                        pool_data[change_type]["tvl"] = tvl

                # Calculation of TVL for THALASWAP
                elif (r"stable_pool::StablePool" in change_type or r"::weighted_pool::WeightedPool" in change_type) and change.write_resource.address==THALASWAP and valid_txn:
                    self.logger.info(change.write_resource.address)
                    provider = "THALASWAP"
                    coin1 , coin2 = "",""
                    try:
                        data = json.loads(change.write_resource.data)
                        coin_x_reserve = int(data['asset_0']["value"])
                        coin_y_reserve = int(data['asset_1']["value"])
                        coin1, coin2 = extract_coins(change_type)
                    except Exception as e:
                        logging.warning(f"Error in {transaction_version} ,{e},{change}")

                    tvl=self.calculate_tvl(coin_x_reserve, coin_y_reserve,provider,change_type)
                    if change_type in pool_data:
                        pool_data[change_type]["tvl"] = tvl
                    # Update TVL in pool_data if it exists
                    if change_type in pool_data:
                        pool_data[change_type]["tvl"] = tvl
                elif "0xc7efb4076dbe143cbcd98cfaaa929ecfc8f299203dfff63b95ccb6bfe19850fa::swap::TokenPairReserve" in change_type and change.write_resource.address==PANCAKE and valid_txn:
                    provider = "PANCAKE"
                    data = json.loads(change.write_resource.data)
                    coin_x_reserve = int(data['reserve_x'])
                    coin_y_reserve = int(data['reserve_y'])
                    # Calculate TVL if both prices are available
                    tvl = self.calculate_tvl(coin_x_reserve, coin_y_reserve,provider,change_type)   
                    # Update TVL in pool_data if it exists
                    if change_type in pool_data:
                        pool_data[change_type]["tvl"] = tvl
                elif "0x31a6675cbe84365bf2b0cbce617ece6c47023ef70826533bde5203d32171dc3c::swap::TokenPairReserve" in change_type and change.write_resource.address==SUSHISWAP and valid_txn:
                    provider = "SUSHISWAP"
                    data = json.loads(change.write_resource.data)
                    coin_x_reserve = int(data['reserve_x'])
                    coin_y_reserve = int(data['reserve_y'])
                    tvl = self.calculate_tvl(coin_x_reserve, coin_y_reserve,provider,change_type)   

                    # Update TVL in pool_data if it exists
                    if change_type in pool_data:
                        pool_data[change_type]["tvl"] = tvl

        processing_duration_in_secs = perf_counter() - start_time
        start_time = perf_counter()
        self.insert_to_db(pool_data)
        # db_insertion_duration_in_secs = perf_counter() - start_time

        return ProcessingResult(
            start_version=start_version,
            end_version=end_version,
            processing_duration_in_secs=processing_duration_in_secs,
            db_insertion_duration_in_secs=1,
            # db_insertion_duration_in_secs=db_insertion_duration_in_secs,
        )

    def insert_to_db(self, parsed_objs: dict) -> None:
        try:
            # Define the order of columns
            columns = [
                'version', 'pool_name', 'timestamp', 'pool_address', 'coin1', 'coin2', 'provider', 'slippage', 'volume', 'delta_x', 'price_x', 'delta_y', 'price_y', 'decimal_x', 'fees', 'tvl'\
                'volume', 'delta_x', 'price_x', 'delta_y', 'price_y', 'decimal_x',
                'fees', 'tvl', 'slippage'
            ]

            # Collect records into a list of tuples
            records = [
                (
                    obj['version'],
                     obj['pool_name'],
                    obj['timestamp'],
                    obj['pool_address'],
                    obj['coin1'],
                    obj['coin2'],
                    obj['provider'],
                    obj['volume'],
                    obj['delta_x'],
                    obj['price_x'],
                    obj['delta_y'],
                    obj['price_y'],
                    obj['decimal_x'],
                    obj['fees'],
                    obj['tvl'],
                    obj['slippage'],
                )
                for obj in parsed_objs.values()
            ]

            # Define the SQL query with positional parameters
            insert_query = """
            INSERT INTO aptos_transactions (
                version, pool_name, timestamp, pool_address, coin1, coin2, provider,
                volume, delta_x, price_x, delta_y, price_y, decimal_x, fees, tvl, slippage
            ) VALUES %s
            ON CONFLICT (version, pool_address) DO UPDATE SET
                pool_name = EXCLUDED.pool_name,
                timestamp = EXCLUDED.timestamp,
                volume = EXCLUDED.volume,
                delta_x = EXCLUDED.delta_x,
                price_x = EXCLUDED.price_x,
                delta_y = EXCLUDED.delta_y,
                price_y = EXCLUDED.price_y,
                decimal_x = EXCLUDED.decimal_x,
                fees = EXCLUDED.fees,
                tvl = EXCLUDED.tvl,
                slippage = EXCLUDED.slippage;
                 """

            with DatabaseManager(DB_STRING) as connection:
                with connection.cursor() as cursor:
                    # Execute the batch insert
                    execute_values(
                        cursor,
                        insert_query,
                        records,
                        page_size=1000  # Adjust batch size as needed
                    )

                        
        except psycopg2.Error as e:
            self.logger.error(f"Database error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
            raise

