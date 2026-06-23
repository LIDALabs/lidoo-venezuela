from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
from odoo import fields
import requests
import logging
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


def get_bcv_rate_of_the_day(self):
    """This function return the rate of the day by the BCV website

    Returns:
        dict: {
            'rates': {'USD': float, 'EUR': float, ...} or None,
            'date': date object or False,
            'error': None or {'type': str, 'message': str}
        }
    """

    disable_warnings(InsecureRequestWarning)
    URL = "https://www.bcv.org.ve/"
    current_date = fields.Date.context_today(self)

    try:
        response = requests.get(URL, verify=False, timeout=5)
        
        # Check HTTP status
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}: {response.reason}"
            _logger.error(f"BCV API error: {error_msg}")
            return {
                'rates': None,
                'date': False,
                'error': {'type': str(response.status_code), 'message': error_msg}
            }
        
        soup = BeautifulSoup(response.text, "html.parser")

        # Parse USD
        usd_container = soup.find(id="dolar")
        if not usd_container:
            error_msg = "USD container not found in BCV response"
            _logger.error(error_msg)
            return {
                'rates': None,
                'date': False,
                'error': {'type': 'ParsingError', 'message': error_msg}
            }
        
        usd_value = (
            usd_container.text.replace("\n", "").replace("USD", "").replace(",", ".").strip()
        )

        # Parse EUR
        eur_container = soup.find(id="euro")
        eur_value = (
            eur_container.text.replace("\n", "").replace("EUR", "").replace(",", ".").strip()
        ) if eur_container else "0.0"

        # Parse CNY
        cny_container = soup.find(id="yuan")
        cny_value = (
            cny_container.text.replace("\n", "").replace("CNY", "").replace(",", ".").strip()
        ) if cny_container else "0.0"

        # Parse RUB
        rub_container = soup.find(id="rublo")
        rub_value = (
            rub_container.text.replace("\n", "").replace("RUB", "").replace(",", ".").strip()
        ) if rub_container else "0.0"

        # Parse TRY
        try_container = soup.find(id="lira")
        try_value = (
            try_container.text.replace("\n", "").replace("TRY", "").replace(",", ".").strip()
        ) if try_container else "0.0"
        
        return {
            'rates': {
                "USD": float(usd_value),
                "EUR": float(eur_value),
                "CNY": float(cny_value),
                "RUB": float(rub_value),
                "TRY": float(try_value),
            },
            'date': current_date,
            'error': None
        }
        
    except requests.exceptions.Timeout as e:
        error_msg = f"Request timeout: {str(e)}"
        _logger.error(error_msg)
        return {
            'rates': None,
            'date': False,
            'error': {'type': 'Timeout', 'message': error_msg}
        }
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error: {str(e)}"
        _logger.error(error_msg)
        return {
            'rates': None,
            'date': False,
            'error': {'type': 'ConnectionError', 'message': error_msg}
        }
    except ValueError as e:
        error_msg = f"Value parsing error: {str(e)}"
        _logger.error(error_msg)
        return {
            'rates': None,
            'date': False,
            'error': {'type': 'ValueError', 'message': error_msg}
        }
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        _logger.error(error_msg)
        return {
            'rates': None,
            'date': False,
            'error': {'type': 'Unknown', 'message': error_msg}
        }
