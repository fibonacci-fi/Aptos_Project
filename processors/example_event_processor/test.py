import requests
import psycopg2
import pandas as pd
def get_liquidswap_rate(coin_address: str, amount) -> float:
    # Set up endpoint, API key, and headers
    end_point = "https://api.panora.exchange/prices"
    api_key = "a4^KV_EaTf4MW#ZdvgGKX#HUD^3IFEAOV_kzpIE^3BQGA8pDnrkT7JcIy#HNlLGi"
    headers = {
        "x-api-key": api_key,
    }
    
    # Configure query parameters
    query = {
        "tokenAddress": coin_address,
    }
    
    # Make the API request
    try:
        response = requests.get(end_point, headers=headers, params=query)
        response.raise_for_status()
        print(response.json())  # Raise an error for bad responses
        data = response.json()[0]
        print(data)
        # Return the USD price if it exists in the response
        usd_price = data.get("usdPrice")
        if usd_price:
            return float(usd_price)
        else:
            raise ValueError("USD price not found in the response.")
    
    except requests.exceptions.RequestException as e:
        print("API request failed:", e)
        return 0.0

import psycopg2
import csv


def fetch_latest_transactions():
    # Establish a connection to the database
    conn = psycopg2.connect("postgresql://team:hiCP]-J_)btL<l-}@34.28.113.224:5432/epochforge")
    
    # Create a cursor object
    cur = conn.cursor()
    
    # Execute a SQL query to fetch the latest 1000 rows from the aptos_transactions table
    cur.execute("""
        SELECT * FROM aptos_transactions
        ORDER BY timestamp DESC
        LIMIT 10000
    """)
    
    # Fetch the column names and results
    col_names = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    # Convert the data to a DataFrame and save to CSV
    df = pd.DataFrame(rows, columns=col_names)
    df.to_csv("txns2.csv", index=False)  # Save without the index column
    
    # Close the cursor and the database connection
    cur.close()
    conn.close()

# Call the function
# fetch_latest_transactions()

# print(get_liquidswap_rate("0x159df6b7689437016108a019fd5bef736bac692b6d4a1f10c941f6fbb9a74ca6::oft::CakeOFT",amount=1))


# import requests
# import json

# # Define the Aptos mainnet API endpoint
# url = "https://api.mainnet.aptoslabs.com/v1/view"

# # Prepare the request payload
# payload = {
#     "jsonrpc": "2.0",
#     "method": "view",
#     "params": {
#         "function": "0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12::scripts_v2::get_dex_fees_in_a_pair",
#         "type_arguments": [
#             "0x84d7aeef42d38a5ffc3ccef853e1b82e4958659d16a7de736a29c55fbbeb0114::staked_aptos_coin::StakedAptosCoin",
#             "0x1::aptos_coin::AptosCoin"
#         ],
#         "arguments": [],
#     },
#     "id": 1
# }

# # Set the headers for the POST request
# headers = {
#     "Content-Type": "application/json"
# }

# # Make the POST request to Aptos fullnode API
# response = requests.post(url, headers=headers, data=json.dumps(payload))

# # Check if the request was successful
# if response.status_code == 200:
#     # Parse and print the response
#     result = response.json()
#     print("Response:", json.dumps(result, indent=2))
# else:
#     print("Error:", response.status_code, response.text)



import binascii
import codecs

def decode_payload(encoded_payload):
    """
    Decodes an encoded payload string into a readable format.
    
    Parameters:
    encoded_payload (str): The encoded payload string to be decoded.
    
    Returns:
    str: The decoded payload string.
    """
    # Remove any whitespace from the input string
    encoded_payload = encoded_payload.strip()
    
    try:
        # Try decoding the payload as bytes
        decoded_payload = encoded_payload.encode('latin-1').decode('utf-8')
        return decoded_payload
    except (UnicodeDecodeError, UnicodeEncodeError):
        return "Unable to decode payload"
    
payload = r'''Kõr;Äx\Ü¹áî$ïH>}"òÙbomö+Ñrouterget_amounts_out¥E íÂpO,ïAzÑuj¡j¦ú®Ñ:ôi¾ßÊÅ¢.!.»,ÊÅà'¨ âåöV£¤#jHÙ>É¶Õpü ß'''
decoded_payload = decode_payload(payload)
print(decoded_payload)