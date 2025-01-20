import os
import hmac
import hashlib
import base64
import time
import json
import requests
import logging


class KuCoinSigner:
    """
    Deze class bevat logica voor het genereren van headers en tekens voor KuCoin API-authenticatie.
    """

    def __init__(self, api_key: str, api_secret: str, api_passphrase: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_passphrase = self._sign(api_passphrase)

        if not all([api_key, api_secret, api_passphrase]):
            logging.warning("API-sleutels ontbreken! Publieke API-toegang is beperkt.")

    def _sign(self, plain_text: str) -> str:
        """
        Hmac SHA256 signing-helper.
        """
        return base64.b64encode(
            hmac.new(self.api_secret.encode('utf-8'), plain_text.encode('utf-8'), hashlib.sha256).digest()
        ).decode('utf-8')

    def generate_headers(self, method: str, endpoint: str, body: str = "") -> dict:
        """
        Genereer vereiste headers voor een API-aanroep.
        """
        timestamp = str(int(time.time() * 1000))
        str_to_sign = f"{timestamp}{method.upper()}{endpoint}{body}"
        signature = self._sign(str_to_sign)

        return {
            "KC-API-KEY": self.api_key,
            "KC-API-SIGN": signature,
            "KC-API-TIMESTAMP": timestamp,
            "KC-API-PASSPHRASE": self.api_passphrase,
            "KC-API-KEY-VERSION": "2",
            "Content-Type": "application/json"
        }


def place_isolated_margin_order(signer: KuCoinSigner, symbol: str, side: str, size: float, leverage: int = 5, clientOid: str = None, autoRepay: bool = False,  type: str = "limit"):
    """
    Plaatst een marge-order via KuCoin's officiële "Isolated Margin" API.

    Parameters:
        signer (KuCoinSigner): Signer-object voor authenticatie.
        symbol (str): Handels paar zoals 'BTC-USDT'.
        side (str): 'buy' of 'sell'.
        size (float): Hoeveelheid om te handelen.
        leverage (int): Marge-hefboom (standaard: 5).
        clientOid (str): Unieke identifier voor de order. Genereert automatisch als niet opgegeven.
        autoRepay (bool): Optioneel; standaard False. Geeft aan of automatisch terugbetaald moet worden.
        stp (str): Optioneel; standaard None. Self-trade prevention parameter.
        type (str): Ordertype, standaard "limit".
    """
    endpoint = "/api/v3/hf/margin/order"
    url = f"https://api.kucoin.com{endpoint}"
    method = "POST"

    # Marge-order payload
    if clientOid is None:
        import uuid
        clientOid = str(uuid.uuid4())

    body = json.dumps({
        "symbol": symbol,
        "side": side,
        "size": str(size),
        "leverage": str(leverage),
        "tradeType": "MARGIN_TRADE",  # Markeer als een marge-trade
        "isIsolated": True,
        "type": "market",
        "autoBorrow": True,  # Activeer automatisch lenen indien nodig
        "clientOid": clientOid,
        "autoRepay": autoRepay
    })


    headers = signer.generate_headers(method, endpoint, body)

    # API-verzoek
    response = requests.post(url, headers=headers, data=body)

    if response.status_code == 200:
        response_data = response.json()
        if "msg" in response_data:
            logging.error(f"API Foutbericht: {response_data['msg']}")
            return response_data
        logging.info("Order succesvol geplaatst.")
        return response_data
    else:
        logging.error(f"Fout bij het plaatsen van de order: {response.status_code} - {response.text}")
        raise RuntimeError(f"Fout bij het plaatsen van de order: {response.status_code} - {response.text}")


if __name__ == "__main__":
    # Zorg ervoor dat deze omgevingsvariabelen correct zijn ingesteld
    api_key = os.getenv("KUCOIN_API_KEY", "")
    api_secret = os.getenv("KUCOIN_API_SECRET", "")
    api_passphrase = os.getenv("KUCOIN_API_PASSPHRASE", "")

    if not api_key or not api_secret or not api_passphrase:
        raise EnvironmentError("API-sleutels ontbreken! Controleer uw .env-bestand of omgevingsvariabelen.")

    signer = KuCoinSigner(api_key, api_secret, api_passphrase)

    # VOORBEELD: Plaats een marge-order met geïsoleerde marge
    try:
        response = place_isolated_margin_order(signer, "BTC-USDT", "buy", 0.001, 5)
        print(json.dumps(response, indent=2))
    except RuntimeError as e:
        logging.error(e)
