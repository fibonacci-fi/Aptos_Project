import requests
import subprocess
from scripts.liquidswap_smart_router import get_liquidswap_rate
import dotenv
import os

dotenv.load_dotenv()


def price_thalaswap(coin):
    """Fetch the price using Thalaswap."""
    try:
        command = f'node scripts/thalaswap_router.mjs "{coin}" "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC" 1'
        print(f"Executing command: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        else:
            print(f"Error from Thalaswap command: {result.stderr}")
    except Exception as e:
        print(f"Exception in price_thalaswap: {e}")
    return 0.0


def get_price(coin_address: str, amount, provider=None) -> float:
    """Fetch the price for a given coin address."""
    # Try fetching from Panora API
    try:
        panora_endpoint = "https://api.panora.exchange/prices"
        api_key = os.getenv("PANORA_API_KEY")

        headers = {"x-api-key": api_key}
        response = requests.get(panora_endpoint, headers=headers, params={"tokenAddress": coin_address})
        response.raise_for_status()

        # Parse and return Panora API result
        data = response.json()
        if data and isinstance(data, list) and "usdPrice" in data[0]:
            print(f"Price from Panora API: {data[0]['usdPrice']}")
            return float(data[0]["usdPrice"])
        else:
            print("Panora API response is missing 'usdPrice'.")
    except requests.RequestException as e:
        print(f"Error fetching price from Panora API: {e}")

    # Fallback to provider
    if provider:
        try:
            print(f"Falling back to provider: {provider}")
            if provider == "liquidswap":
                return get_liquidswap_rate(coin_address, amount)
            elif provider == "thalaswap":
                return price_thalaswap(coin_address)
            else:
                print(f"Unknown provider: {provider}")
        except Exception as e:
            print(f"Provider error: {e}")

    # If all fails, return 0.0
    print("All attempts to fetch the price failed.")
    return 0.0


# Example usage
# price = get_price(
#     coin_address="0x84d7aeef42d38a5ffc3ccef853e1b82e4958659d16a7de736a29c55fbbeb0114::staked_aptos_coin::StakedAptosCoin",
#     amount=1,
#     provider="thalaswap"
# )
# print(f"Final price: {price}")
