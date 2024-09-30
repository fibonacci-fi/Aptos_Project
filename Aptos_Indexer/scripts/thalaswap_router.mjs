import { ThalaswapRouter } from "@thalalabs/router-sdk";
import { Network } from "@aptos-labs/ts-sdk";

// Check if the required parameters are provided
if (process.argv.length < 5) {
    console.error("Usage: node script.mjs <fromToken> <toToken> <amount>");
    process.exit(1);
}

// Get parameters from command line arguments
const [fromToken, toToken, amountStr] = process.argv.slice(2);
const amountIn = parseFloat(amountStr);

if (isNaN(amountIn)) {
    console.error("Invalid amount provided.");
    process.exit(1);
}

// Define required parameters for ThalaswapRouter
const network = Network.MAINNET; // Ensure this matches the actual enum value
const fullnode = "https://fullnode.mainnet.aptoslabs.com/v1";
const resourceAddress = "0x48271d39d0b05bd6efca2278f22277d6fcc375504f9839fd73f74ace240861af"; // Replace with actual resource address
const multirouterAddress = "0x60955b957956d79bc80b096d3e41bad525dd400d8ce957cdeb05719ed1e4fc26"; // Replace with actual multirouter address

// Instantiate ThalaswapRouter with the required parameters
const router = new ThalaswapRouter(
  network,
  fullnode,
  resourceAddress,
  multirouterAddress
);

async function getSwapRoute(fromToken, toToken, amountIn) {
    try {
        const route = await router.getRouteGivenExactInput(fromToken, toToken, amountIn);
        
        // Check if route is defined and has amountOut
        if (route && typeof route.amountOut === 'number') {
            // Output only the amountOut value
            console.log(route.amountOut);
        } else {
            console.error("Route or amountOut is undefined or invalid.");
            console.log("Route:", route);
        }
    } catch (error) {
        console.error("Error fetching route:", error);
    }
}

// Call the function with the provided parameters
getSwapRoute(fromToken, toToken, amountIn);
