import os
from kucoin.client import Client
from kucoin_utils import get_isolated_margin_balance_http
from dotenv import load_dotenv
import pandas as pd
from ta.trend import SMAIndicator
import time
import requests
from urllib3.util.connection import allowed_gai_family
from place_isolated_margin_order import place_isolated_margin_order, KuCoinSigner





# Forceer alleen IPv4 voor alle verbindingen
def configure_ipv4():
    """
    Gebruik alleen IPv4 in combinaties met urllib3.
    """
    try:
        # Pas de allowed_gai_family aan om alleen IPv4 toe te staan
        import socket
        original_allowed_gai_family = allowed_gai_family

        def forced_ipv4_only():
            return socket.AF_INET  # Forceer IPv4

        requests.packages.urllib3.util.connection.allowed_gai_family = forced_ipv4_only
        return original_allowed_gai_family
    except Exception as e:
        print(f"Waarschuwing: IPv4-afdwinging is mislukt. {e}")
        return None


# Configureer IPv4
configure_ipv4()

# Laad API-sleutels van .env-bestand
load_dotenv()
API_KEY = os.getenv("KUCOIN_API_KEY")
API_SECRET = os.getenv("KUCOIN_API_SECRET")
API_PASSPHRASE = os.getenv("KUCOIN_API_PASSPHRASE")

if not API_KEY or not API_SECRET or not API_PASSPHRASE:
    raise EnvironmentError("API-sleutels ontbreken. Controleer of deze correct in het .env-bestand staan.")

# Maak een client-object met jouw API-sleutels
client = Client(API_KEY, API_SECRET, API_PASSPHRASE)


def fetch_ohlcv(symbol="ADA-USDT", granularity=900, limit=50):
    # Mapping van granularity in seconden naar kline_type
    granularity_map = {
        60: '1min',
        180: '3min',
        300: '5min',
        900: '15min',
        1800: '30min',
        3600: '1hour',
        7200: '2hour',
        14400: '4hour',
        21600: '6hour',
        28800: '8hour',
        43200: '12hour',
        86400: '1day',
        604800: '1week'
    }

    if granularity not in granularity_map:
        raise ValueError(f"Invalid granularity '{granularity}'. Valid options are: {list(granularity_map.keys())}.")

    kline_type = granularity_map[granularity]

    # Bereken start- en eindtijd (tijdstempels)
    end_time = int(time.time())  # Huidige Unix-tijd
    start_time = end_time - (limit * granularity)  # Tijdstempel voor 'limit' periodes geleden

    # Haal kline data op
    klines = client.get_kline_data(symbol, kline_type, start=start_time, end=end_time)
    if klines:
        # Maak een DataFrame zonder vooraf bepaalde kolommen
        df = pd.DataFrame(klines)
        print(f"Opgehaalde kolommen: {df.columns}")

        # Definieer kolomnamen als ze exact overeenkomen
        expected_columns = ["timestamp", "open", "close", "high", "low", "volume"]
        if len(df.columns) >= len(expected_columns):
            df.columns = expected_columns + [f"extra_col_{i}" for i in range(len(df.columns) - len(expected_columns))]
        else:
            raise ValueError("API retourneert minder kolommen dan verwacht.")

        # Verwerk data
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="s")  # Timestamps omzetten naar datetime
        df = df.sort_values(by="timestamp")  # Sorteer op tijd
        df[["open", "close", "high", "low", "volume"]] = df[["open", "close", "high", "low", "volume"]].astype(float)
        return df
    else:
        raise Exception("Kan OHLCV gegevens niet ophalen. Controleer je API-sleutels, netwerkverbinding of API request parameters.")


def calculate_sma(data, period=20):
    """
    Bereken de SMA gebruikmakend van ta.trend.SMAIndicator.

    Parameters:
        data (pd.DataFrame): DataFrame met OHLCV-gegevens.
        period (int): De periode voor de SMA-berekening.

    Returns:
        pd.DataFrame: DataFrame met een extra kolom 'sma' (Simple Moving Average).
    """
    sma = SMAIndicator(data["close"], window=period)
    data["sma"] = sma.sma_indicator()
    return data


def get_balance(symbol="ADA-USDT"):
    """
    Haalt de beschikbare margebalans (Isolated Margin) op voor een specifiek handelspaar.

    Parameters:
        symbol (str): Handels paar zoals "ADA-USDT".

    Returns:
        float: Beschikbare margebalans voor de trading asset.
    """
    try:
        available_balance = get_isolated_margin_balance_http(symbol)
        return float(available_balance)
    except Exception as e:
        print(f"Fout bij ophalen van Isolated Margin saldo: {e}")
        return 0.0


def margin_trade(symbol="ADA-USDT", size=10, leverage=5):
    """
    Voer geïsoleerde margehandel uit op basis van een SMA-strategie.

    Parameters:
        symbol (str): Handels paar zoals "ADA-USDT".
        size (float): Ordergrootte voor de handel.
        leverage (int): Hefboomwerking die moet worden gebruikt.
    """
    try:
        # Haal balans op
        balance = get_balance(symbol)
        print(f"Huidig saldo voor {symbol}: {balance} {symbol.split('-')[0]}")

        if balance < 2:  # Minimaal saldovereiste
            print("Onvoldoende saldo om te handelen.")
            return

        # Haal OHLCV-data op en bereken SMA
        df = fetch_ohlcv(symbol)
        df = calculate_sma(df)
        print(df.tail())  # Print laatste waarden voor debugging

        # Haal de laatste prijs en SMA
        last_close = df["close"].iloc[-1]
        last_sma = df["sma"].iloc[-1]

        print(f"Laatste prijs: {last_close}, Laatste SMA: {last_sma}")

        # Maak een nieuwe signer instantie
        signer = KuCoinSigner(API_KEY, API_SECRET, API_PASSPHRASE)

        # Bepaal of er een trade moet worden gedaan
        if last_close > last_sma:
            print(f"{symbol} prijs ligt boven de SMA. Een LONG-order wordt geplaatst.")
            place_isolated_margin_order(signer, symbol, "buy", size=size, leverage=leverage)
        elif last_close < last_sma:
            print(f"{symbol} prijs ligt onder de SMA. Een SHORT-order wordt geplaatst.")
            place_isolated_margin_order(signer, symbol, "sell", size=size, leverage=leverage)
        else:
            print(f"{symbol} prijs is gelijk aan de SMA. Geen actie ondernomen.")
    except Exception as e:
        print(f"Fout tijdens de margehandel: {e}")




if __name__ == "__main__":
    margin_trade("ADA-USDT")
