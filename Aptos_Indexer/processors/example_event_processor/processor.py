from aptos_protos.aptos.transaction.v1 import transaction_pb2
from processors.example_event_processor.models import Event
from typing import List
from utils.transactions_processor import ProcessingResult
from utils import general_utils
from utils.transactions_processor import TransactionsProcessor
from utils.models.schema_names import EXAMPLE
from utils.session import Session
from utils.processor_name import ProcessorName
from time import perf_counter
from processors.example_event_processor.helpers import escaped_string_to_hex
import json
import pandas as pd
import subprocess
from dotenv import load_dotenv
import psycopg2 , os
import yaml
from constants import COINS, PROTOCOLS
import logging
load_dotenv()

# Access environment variables
DB_STRING ="postgresql://team:hiCP]-J_)btL<l-}@34.28.113.224:5432/epochforge"

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
def price_liquidswap(coin,amount):
    division_factor=10**6
    try:
        if coin == "0xdd89c0e695df0692205912fb69fc290418bed0dbe6e4573d744a6d5e6bab6c13::coin::T":
            print("Coin is sol so changing amount to 100000")
            amount = 1000
            division_factor=10
        res=subprocess.run("pwd", shell=True, capture_output=True, text=True)
        print(res.stdout)
        # Define the command to be executed
        print(coin)
        command = f'node scripts/liquidswap_router.mjs "{coin}" "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC" {amount}'
        print(command)
        # Execute the command
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        print(result)
        # Check if the command was successful
        if result.returncode == 0:
            # Parse and return the price from the output
            return (int(result.stdout.strip()))/division_factor
        else:
            # Print the error and return None
            print(f"Error executing command: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception occurred: {e}")
        return None
    
def price_thalaswap(coin):
    try:
        # Define the command to be executed
        command = f'node scripts/thalaswap_router.mjs "{coin}" "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC" {1}'
        print(command)
        # Execute the command
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        # Check if the command was successful
        if result.returncode == 0:
            amt = float(result.stdout.strip())
            print(amt)
            return amt
        else:
            # Print the error and return None
            print(f"Error executing command: {result.stderr}")
            return None
    except Exception as e:
        print(f"Exception occurred: {e}")
        return None
    
def extract_coins(type_str):
    coin_list = type_str.split('<')[1].split('>')[0]
    coins = [coin.strip() for coin in coin_list.split(',')]
    return coins[0], coins[1]

#==============================CONSTANTS==================================================

# Load the config.yaml file
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# Access the constants
USDC_ADDRESS = COINS['USDC_ADDRESS']
thAPT = COINS['thAPT']
APTOS = COINS['APTOS']
MOD = COINS['MOD']
SOL = COINS['SOL']

THALASWAP = PROTOCOLS['THALASWAP']
LIQUIDSWAP = PROTOCOLS['LIQUIDSWAP']
PANCAKE = PROTOCOLS['PANCAKE']

Decimals_9 = [APTOS, MOD, SOL , thAPT]
print(Decimals_9)
#==================================================================================================
class ExampleEventProcessor(TransactionsProcessor):
    def __init__(self) -> None:
        super().__init__()
        self.logger = logging.getLogger(__name__)
    def name(self) -> str:
        return ProcessorName.EXAMPLE_EVENT_PROCESSOR.value

    def schema(self) -> str:
        return EXAMPLE

    def process_transactions(
        self,
        transactions: list[transaction_pb2.Transaction],
        start_version: int,
        end_version: int,
    ) -> ProcessingResult:
        
        event_db_objs: List[Event] = []
        start_time = perf_counter()
        tvl_data = []
        pool_data = {}
        # print(transactions)
        price_cache = {}
        for transaction in transactions:
            # Custom filtering
            # Here we filter out all transactions that are not of type TRANSACTION_TYPE_USER
            if transaction.type != transaction_pb2.Transaction.TRANSACTION_TYPE_USER:
                continue
            changes=transaction.info.changes
            transaction_version = transaction.version
            transaction_block_height = transaction.block_height
            transaction_timestamp = general_utils.parse_pb_timestamp(transaction.timestamp)
            user_transaction = transaction.user
            status=transaction.info.success
            fees=float((transaction.info.gas_used)/1000000)
            transaction_hash=transaction.info.hash.hex()
            if not status:
                continue
            print("Processing events")
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
                        coin1, coin2 = extract_coins(type)
                        
                        div_factor1 = 100000000 if coin1 in Decimals_9 else 1000000
                        div_factor2 = 100000000 if coin2 in Decimals_9 else 1000000
                        print(coin1 , div_factor1)
                        # ========== LIQUIDSWAP VOLUME CALCULATION  =============================               
                        if account_address == LIQUIDSWAP:
                            valid_txn = True
                            provider = "LIQUIDSWAP"

                            pool_id = pool_id.replace("SwapEvent", "LiquidityPool")
                            data["x_in"] = int(data["x_in"]) / div_factor1
                            data["x_out"] = int(data["x_out"]) / div_factor1
                            data["y_out"] = int(data["y_out"]) / div_factor2  
                            data["y_in"] = int(data["y_in"]) / div_factor2  

                            # Calculate expected output based on input and price
                            price_x = 1 if coin1 == USDC_ADDRESS else price_cache.get(coin1)
                            price_y = 1 if coin2 == USDC_ADDRESS else price_cache.get(coin2)

                            if price_x is None:
                                try:
                                    price_x = price_liquidswap(coin1, div_factor1)
                                    price_cache[coin1] = price_x
                                except Exception as e:
                                    print(f"Error fetching price for {coin1}: {e}")
                                    price_x = 0

                            if price_y is None:
                                try:
                                    price_y = price_liquidswap(coin2, div_factor2)
                                    price_cache[coin2] = price_y
                                except Exception as e:
                                    print(f"Error fetching price for {coin2}: {e}")
                                    price_y = 0

                            # Calculate actual delta for X and Y
                            delta_x = abs(float(data["x_in"] - data["x_out"]))
                            delta_y= abs(float(data["y_in"] - data["y_out"]))

                            # Calculate expected delta Y using the price-based formula: ΔX * PriceX = ΔY_expected * PriceY
                            delta_y_expected = (delta_x * price_x) / price_y if price_y != 0 else 0

                            # Calculate slippage: (Expected Output - Actual Output) / Expected Output * 100
                            slippage = ((delta_y_expected - delta_y) / delta_y_expected) * 100 if delta_y_expected != 0 else 0

                            # Log or print the slippage
                            print(price_x,price_y,f"Slippage: {slippage:.2f}%")

                            # Calculate volume
                            Vol = delta_x * price_x  # type: ignore
                        elif account_address == THALASWAP:
                            valid_txn = True
                            provider = "THALASWAP"
                            
                            if "weighted_pool" in pool_id:
                                pool_id = pool_id.replace("SwapEvent", "WeightedPool")
                            else:
                                pool_id = pool_id.replace("SwapEvent", "StablePool")
                            
                            # Extract and normalize input amount (Delta X)
                            delta_x = int(data['amount_in']) / div_factor1
                            
                            # Fetch current price for Coin X
                            price_x = 1 if coin1 == USDC_ADDRESS else price_cache.get(coin1)
                            if price_x is None:
                                try:
                                    price_x = price_thalaswap(coin1)
                                    price_cache[coin1] = price_x
                                except Exception as e:
                                    print(f"Error fetching price for {coin1}: {e}")
                                    price_x = 0
                            
                            # Fetch current price for Coin Y
                            price_y = 1 if coin2 == USDC_ADDRESS else price_cache.get(coin2)
                            if price_y is None:
                                try:
                                    price_y = price_thalaswap(coin2)
                                    price_cache[coin2] = price_y
                                except Exception as e:
                                    print(f"Error fetching price for {coin2}: {e}")
                                    price_y = 0


                                                        # Calculate actual delta for Y (Delta Y Actual)
                            delta_y = int(data['amount_out']) / div_factor2
                            delta_y_expected = (delta_x * price_x) / price_y if price_y != 0 else 0

                            # Calculate slippage: (Expected Output - Actual Output) / Expected Output * 100
                            slippage = ((delta_y_expected - delta_y) / delta_y_expected) * 100 if delta_y_expected != 0 else 0

                            # Log or print the slippage
                            print(price_x,price_y,f"Slippage: {slippage:.2f}%")


                            # Calculate volume
                            Vol = delta_x * price_x  # type: ignore

                        elif account_address == PANCAKE:
                            
                            pool_id = pool_id.replace("SwapEvent","TokenPairReserve")
                            data["amount_x_in"] = int(data["amount_x_in"]) / div_factor1
                            data["amount_x_out"] = int(data["amount_x_out"]) / div_factor1
                            delta_x = data["amount_x_in"] - data["amount_x_out"]
                            # provider = "PANCAKE"
                        if provider:
                            if pool_id in pool_data:
                                pool_data[pool_id]["volume"] += Vol
                                pool_data[pool_id]["price"] = price_x
                            else:
                                pool_data[pool_id] = {
                                    "version": transaction_version,
                                    "timestamp": transaction_timestamp,
                                    "pool_address": pool_id.replace(" ",""),
                                    "coin1": coin1,
                                    "coin2": coin2,
                                    "provider": provider,
                                    'slippage':float(round(abs(slippage),2)),
                                    "volume": Vol,
                                    "delta_x":delta_x,
                                    "price_x": price_x,
                                    "fees": fees,
                                    "tvl": None,
                                }
                    except Exception as e:
                        print(f"Error processing swap event: {e}")
                        print(f"Type: {type} Version {transaction_version}")
                # if type =="0x1::transaction_fee::FeeStatement":
                #     fees = int(data['total_charge_gas_units'])/1000000
                #     print(transaction_hash , "Fees",fees)

# =============================================================================================================================
# =============================================================================================================================



            for change in changes:
                change_type = change.write_resource.type_str
                
                # Calculation of TVL for Liquidswap

                if "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::liquidity_pool::LiquidityPool" in change_type:
                    data = json.loads(change.write_resource.data)
                    coin_x_reserve = int(data['coin_x_reserve']['value'])
                    coin_y_reserve = int(data['coin_y_reserve']['value'])
                    coin1, coin2 = extract_coins(change_type)
                    # print(change_type)
                    # Determine the division factors based on the coin types
                    div_factor1 = 100000000 if coin1 in Decimals_9 else 1000000
                    div_factor2 = 100000000 if coin2 in Decimals_9 else 1000000
                    
                    # Convert reserves to float
                    coin_x_reserve = coin_x_reserve / div_factor1
                    coin_y_reserve = coin_y_reserve / div_factor2
                    tvl = 0

                    # Retrieve or calculate price_x
                    if coin1 == USDC_ADDRESS:
                        price_x = 1
                        price_y = price_cache.get(coin2)
                        if price_y is None:
                            try:
                                price_y = price_liquidswap(coin2, div_factor2)
                                price_cache[coin2] = price_y
                            except Exception as e:
                                print(f"Error fetching price for {coin2}: {e}")
                                price_y = 0
                    elif coin2 == USDC_ADDRESS:
                        price_y = 1
                        price_x = price_cache.get(coin1)
                        if price_x is None:
                            try:
                                price_x = price_liquidswap(coin1, div_factor1)
                                price_cache[coin1] = price_x
                            except Exception as e:
                                print(f"Error fetching price for {coin1}: {e}")
                                price_x = 0
                    else:
                        # Neither coin is USDC, fetch prices for both
                        price_x = price_cache.get(coin1)
                        if price_x is None:
                            try:
                                price_x = price_liquidswap(coin1, div_factor1)
                                price_cache[coin1] = price_x
                            except Exception as e:
                                print(f"Error fetching price for {coin1}: {e}")
                                price_x = 0
                        
                        price_y = price_cache.get(coin2)
                        if price_y is None:
                            try:
                                price_y = price_liquidswap(coin2, div_factor2)
                                price_cache[coin2] = price_y
                            except Exception as e:
                                print(f"Error fetching price for {coin2}: {e}")
                                price_y = 0

                    # Calculate TVL if both prices are available
                    if price_x and price_y:
                        tvl = coin_x_reserve * price_x + coin_y_reserve * price_y
                    else:
                        print("Error fetching prices for the tokens.")
                    
                    if change_type in pool_data:
                        pool_data[change_type]["tvl"] = tvl

                # Calculation of TVL for THALASWAP
                if (r"stable_pool::StablePool" in change_type or r"::weighted_pool::WeightedPool" in change_type) and change.write_resource.address==THALASWAP and valid_txn:
                    print(change.write_resource.address)
                    try:
                        data = json.loads(change.write_resource.data)
                        coin_x_reserve = int(data['asset_0']["value"])
                        coin_y_reserve = int(data['asset_1']["value"])
                        coin1, coin2 = extract_coins(change_type)
                    except Exception as e:
                        logging.warning(f"Error in {transaction_version} ,{e},{change}")
                    # Determine the division factors based on the coin types
                    div_factor1 = 100000000 if any(token in coin1 for token in Decimals_9) else 1000000
                    div_factor2 = 100000000 if any(token in coin2 for token in Decimals_9) else 1000000

                    # Convert reserves to float
                    coin_x_reserve = coin_x_reserve / div_factor1
                    coin_y_reserve = coin_y_reserve / div_factor2
                    
                    # Retrieve or calculate price_x and price_y
                    if coin1 == USDC_ADDRESS:
                        price_x = 1
                        price_y = price_cache.get(coin2)
                        if price_y is None:
                            try:
                                price_y = price_thalaswap(coin2)
                                price_cache[coin2] = price_y
                            except Exception as e:
                                print(f"Error fetching price for {coin2}: {e}")
                                price_y = 0
                    elif coin2 == USDC_ADDRESS:
                        price_y = 1
                        price_x = price_cache.get(coin1)
                        if price_x is None:
                            try:
                                price_x = price_thalaswap(coin1)
                                price_cache[coin1] = price_x
                            except Exception as e:
                                print(f"Error fetching price for {coin1}: {e}")
                                price_x = 0
                    else:
                        price_x = price_cache.get(coin1)
                        if price_x is None:
                            try:
                                price_x = price_thalaswap(coin1)
                                price_cache[coin1] = price_x
                            except Exception as e:
                                print(f"Error fetching price for {coin1}: {e}")
                                price_x = 0

                        price_y = price_cache.get(coin2)
                        if price_y is None:
                            try:
                                price_y = price_thalaswap(coin2)
                                price_cache[coin2] = price_y
                            except Exception as e:
                                print(f"Error fetching price for {coin2}: {e}")
                                price_y = 0

                    # Calculate TVL if both prices are available
                    tvl = 0
                    if price_x and price_y:
                        tvl = coin_x_reserve * price_x + coin_y_reserve * price_y
                    else:
                        print("Error fetching prices for the tokens.")

                    # Update TVL in pool_data if it exists
                    if change_type in pool_data:
                        pool_data[change_type]["tvl"] = tvl
        print(pool_data)
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

    def insert_to_db(self, parsed_objs: List) -> None:
        """
        Inserts a list of parsed transaction output objects into the database.

        :param parsed_objs: List of TransactionOutput objects containing parsed transaction details.
        """
        # Establish a connection to the database
        try:
            url = DB_STRING
            print(url)
            connection = psycopg2.connect(url)
            self.logger.info("Database connection established.")

            with connection:
                with connection.cursor() as cursor:
                    # Prepare the SQL query for insertion
                    insert_query = """
                        INSERT INTO aptos_transactions (
                            version, timestamp, pool_address, coin1, coin2, provider, volume,
                            delta_x, price_x, fees, tvl, slippage
                        ) VALUES (
                            %(version)s, %(timestamp)s, %(pool_address)s, %(coin1)s, %(coin2)s, %(provider)s, %(volume)s,
                            %(delta_x)s, %(price_x)s, %(fees)s, %(tvl)s, %(slippage)s
                        )
                        ON CONFLICT (version, pool_address) DO UPDATE SET
                            timestamp = EXCLUDED.timestamp,
                            volume = EXCLUDED.volume,
                            delta_x = EXCLUDED.delta_x,
                            price_x = EXCLUDED.price_x,
                            fees = EXCLUDED.fees,
                            tvl = EXCLUDED.tvl,
                            slippage = EXCLUDED.slippage;
                    """
                    
                    # Insert each parsed object into the database
                    for obj in parsed_objs.values():
                        print(obj)
                        cursor.execute(insert_query, {
                            'version': obj['version'],
                            'timestamp': obj['timestamp'],
                            'pool_address': obj['pool_address'],
                            'coin1': obj['coin1'],
                            'coin2': obj['coin2'],
                            'provider': obj['provider'],
                            'volume': obj['volume'],
                            'delta_x': obj['delta_x'],
                            'price_x': obj['price_x'],
                            'fees': obj['fees'],
                            'tvl': obj['tvl'],
                            'slippage': obj['slippage']  # New field added here
                        })
                    connection.commit()
                    self.logger.info(f"Inserted {len(parsed_objs)} records into the database.")

        except psycopg2.Error as e:
            self.logger.error(f"Database error: {e}")
            if connection:
                connection.rollback()
                self.logger.warning("Transaction rolled back due to an error.")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
        finally:
            if connection:
                connection.close()
                self.logger.info("Database connection closed.")
