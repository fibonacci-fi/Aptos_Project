import requests
import pandas as pd

# Define the API endpoint
api_url = "https://api.mainnet.aptoslabs.com/v1/accounts/{address}/resources"

# List of addresses to fetch data from
addresses = [
    "0x61d2c22a6cb7831bee0f48363b0eec92369357aece0d1142062f7d5d85c7bef8",
    "0x05a97986a9d031c4567e15b797be516910cfcb4156312482efc6a19c0a30c948"
]

def fetch_data(address):
    # Make the API request
    response = requests.get(api_url.format(address=address))
    print(response.url)
    # Check if the request was successful
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch data for address {address}: {response.status_code}")
        return []

def extract_coins(type_str):
    coin_list = type_str.split('<')[1].split('>')[0]
    coins = [coin.strip() for coin in coin_list.split(',')]
    return coins[0], coins[1]

def transform_data(item):
    item_type = item['type']
    coin1, coin2 = extract_coins(item_type)
    item_data = item['data']
    coin_x_reserve = float(item_data["coin_x_reserve"]["value"])
    coin_y_reserve = float(item_data["coin_y_reserve"]["value"])
    if 'Stable' in item_type:
        curve = "Stable"
    else:
        curve = "Uncorrelated"
    Amp = 0
    return [item_type, coin1, coin2,curve,Amp]

# Initialize an empty list to store all data
all_data = []

# Fetch and process data for each address
for address in addresses:
    parsed_data = fetch_data(address)
    filtered_data = [item for item in parsed_data if "LiquidityPool" in item['type']]
    transformed_data = [transform_data(item) for item in filtered_data]
    all_data.extend(transformed_data)

# Create DataFrame
all_pools_pd = pd.DataFrame(all_data, columns=["id", "token_a", "token_b","curve","Amp"])
all_pools_pd["provider"] = "LiquidSwap"
all_pools_pd["tvl"] = 0

# Remove duplicates based on the 'id' column
all_pools_pd = all_pools_pd.drop_duplicates(subset='id')

# Save to CSV
csv_file_path = 'Liquidswap_pools.csv'
all_pools_pd.to_csv(csv_file_path, index=False)

print(f"Transformed data saved to {csv_file_path}")
