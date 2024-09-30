import { argv, exit } from 'process';
import {SDK} from "@pontem/liquidswap-sdk"; // Ensure SDK is compatible with ES module imports

export const NODE_URL = "https://fullnode.mainnet.aptoslabs.com/v1";
export const MODULES_ACCOUNT = '0x190d44266241744264b964a37b8f09863167a12d3e70cda39376cfb4e3561e12';
export const RESOURCE_ACCOUNT = '0x05a97986a9d031c4567e15b797be516910cfcb4156312482efc6a19c0a30c948';

// Initialize SDK
const sdk = new SDK({
  nodeUrl: NODE_URL,
  networkOptions: {
    resourceAccount: RESOURCE_ACCOUNT,
    moduleAccount: MODULES_ACCOUNT,
    modules: {
      Scripts: `${MODULES_ACCOUNT}::scripts_v2`,
      CoinInfo: '0x1::coin::CoinInfo',
      CoinStore: '0x1::coin::CoinStore',
    },
  },
});

// Function to calculate rates
export async function calculateRates(token1, token2, amount) {
  try {
    const fromToken = token1;
    const toToken = token2;
    const usdtRate = await sdk.Swap.calculateRates({
      fromToken,
      toToken,
      amount,
      curveType: 'uncorrelated',
      interactiveToken: 'from',
    });
    console.log(usdtRate);
    return usdtRate;
  } catch (error) {
    console.error('Error calculating rates:', error);
    throw error;
  }
}

// Parse command-line arguments
const [, , token1, token2, amountStr] = argv;

if (!token1 || !token2 || !amountStr) {
  console.error('Usage: node liquidswap_router.mjs <token1> <token2> <amount>');
  exit(1);
}

const amount = parseFloat(amountStr);

if (isNaN(amount)) {
  console.error('Invalid amount provided');
  exit(1);
}

// Call the calculateRates function with command-line arguments
calculateRates(token1, token2, amount)
  .catch((error) => {
    console.error('Error:', error);
    exit(1);
  });
