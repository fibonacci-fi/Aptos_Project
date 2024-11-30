import requests
import subprocess

def get_liquidswap_rate(coin1, amount, coin2="0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"):
    # Define the base URL for the API request
    base_url = "https://api.liquidswap.com/smart-router"
    
    # Set up the query parameters
    params = {
        "from": coin1,
        "to": coin2,
        "cl": "true",
        "input": int(amount),
    }

    # Custom headers
    headers = {
        "accept": "application/json",
        "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6",
        "origin": "https://liquidswap.com",
        "referer": "https://liquidswap.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }

    # Make the GET request to the API
    response = requests.get(base_url, params=params, headers=headers)
    print(response.url)  # Confirm the URL being requested

    # Check if the request was successful
    if response.status_code == 200:
        data = response.json()

        # Prioritize defaultMode
        if "defaultMode" in data and "path" in data["defaultMode"]:
            path_info = data["defaultMode"]["path"][-1]
            output_amount = int(path_info["outputAmount"])
            return output_amount / 10**6  # Convert to human-readable format
        
        # Fallback to directMode
        elif "directMode" in data and "path" in data["directMode"]:
            path_info = data["directMode"]["path"][0]
            output_amount = int(path_info["outputAmount"])
            return output_amount / 10**6  # Convert to human-readable format
        
        else:
            print("Output amount not found in response")
            # Call price_liquidswap if no output amount found
            return price_liquidswap(coin1, amount)  # Fallback to price_liquidswap

    else:
        print(f"Error: Failed to fetch data, status code: {response.status_code}")
        # Call price_liquidswap if request fails
        return price_liquidswap(coin1, amount)  # Fallback to price_liquidswap

def price_liquidswap(coin, amount):
    division_factor = 10**6
    try:
        if coin == "0xdd89c0e695df0692205912fb69fc290418bed0dbe6e4573d744a6d5e6bab6c13::coin::T":
            print("Coin is SOL, changing amount to 100000")
            amount = 1000
            division_factor = 10
        
        # Define the command to be executed
        command = f'node scripts/liquidswap_router.mjs "{coin}" "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC" {amount}'
        print(command)
        
        # Execute the command
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        # Check if the command was successful
        if result.returncode == 0:
            # Parse and return the price from the output
            return int(result.stdout.strip()) / division_factor
        else:
            # Print the error and return 0
            print(f"Error executing command: {result.stderr}")
            return 0
    except Exception as e:
        print(f"Exception occurred: {e}")
        return 0

# Example usage:
# coin1 = "0xae478ff7d83ed072dbc5e264250e67ef58f57c99d89b447efd8a0a2e8b2be76e::coin::T"  # Base coin (T)
# amount = 100000000  # Amount in base coin's smallest unit (e.g., 1 T = 1000000 smallest units)

# # Get the output amount, which will call price_liquidswap if needed
# output_amount = get_liquidswap_rate(coin1, amount)

# print(f"Output Amount (human-readable): {output_amount}")
