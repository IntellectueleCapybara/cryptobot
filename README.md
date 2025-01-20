# KuCoin Trading Bot

This project is a trading bot that interacts with the KuCoin exchange to perform automated trading based on a Simple Moving Average (SMA) strategy. The bot includes functionalities to:

1. Configure the KuCoin exchange using the CCXT library.
2. Test the API connection to KuCoin.
3. Fetch OHLCV data and calculate SMA.
4. Place isolated margin orders based on the trading strategy.

## Project Structure

- `main.py`: The main entry point for running the bot. It includes the trading logic, fetching OHLCV data, calculating SMA, and placing margin trades.
- `kucoin_utils.py`: Contains utility functions for configuring the KuCoin exchange and testing the API connection.
- `place_order.py`: Contains the logic for placing isolated margin orders via the KuCoin API.

## Prerequisites

- Python 3.10 or higher
- KuCoin API keys (API Key, API Secret, API Passphrase)
- A `.env` file with your KuCoin API keys

## Usage

To run the trading bot, execute the following command:
```bash
python main.py
