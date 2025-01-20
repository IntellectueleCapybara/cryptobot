# kucoin_utils.py
import requests
import time
import base64
import hmac
import hashlib
import os


def get_isolated_margin_balance_http(symbol="ADA-USDT"):
    """
    Haalt de beschikbare balans voor een geïsoleerd marge-account rechtstreeks via een HTTP-aanroep.

    Parameters:
        symbol (str): Handelspaar zoals "ADA-USDT".

    Returns:
        float: Beschikbare balans voor het handelspaar.
    """
    try:
        # Haal API-sleutels op uit .env
        api_key = os.getenv("KUCOIN_API_KEY")
        api_secret = os.getenv("KUCOIN_API_SECRET")
        api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE")

        # Stel tijdstempel en endpoint in
        timestamp = int(time.time() * 1000)
        url = "https://api.kucoin.com"
        endpoint = "/api/v1/isolated/accounts"

        # Maak de signing string
        str_to_sign = f"{timestamp}GET{endpoint}"
        signature = base64.b64encode(
            hmac.new(api_secret.encode("utf-8"), str_to_sign.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")

        # Pasphrase encoding
        passphrase = base64.b64encode(
            hmac.new(api_secret.encode("utf-8"), api_passphrase.encode("utf-8"), hashlib.sha256).digest()
        ).decode("utf-8")

        # Stel headers in voor de API-aanroep
        headers = {
            "KC-API-KEY": api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": str(timestamp),
            "KC-API-PASSPHRASE": passphrase,
            "KC-API-KEY-VERSION": "2",
        }

        # Doe de API-aanroep
        response = requests.get(url + endpoint, headers=headers)

        # Controleer of de HTTP-status 200 OK is
        if response.status_code != 200:
            raise Exception(f"API-aanroep mislukt: {response.json()}")

        # Haal de JSON-responsedata op
        data = response.json()

        # Zoek naar het juiste handelspaar in de data
        for account in data['data']['assets']:
            if account['symbol'] == symbol:
                return float(account['baseAsset']['availableBalance'])  # Beschikbare saldo

        return 0.0

    except Exception as e:
        print(f"Fout bij ophalen van Isolated Margin saldo via HTTP: {e}")
        return 0.0