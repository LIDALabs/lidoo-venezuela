from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
from odoo import fields
import requests
import logging
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


def get_bcv_rate_of_the_day(self):
    """This function return the rate of the day by the BCV website

    Raises:
        UserError: Error to connect with BCV, please check your internet connection or try again later

    Returns:
        tuple (float: rate of the day, date: date of the rate)
    """

    disable_warnings(InsecureRequestWarning)
    URL = "https://www.bcv.org.ve/"
    current_date = fields.Date.context_today(self)

    try:
        html_content = requests.get(URL, verify=False, timeout=5)
        soup = BeautifulSoup(html_content.text, "html.parser")

        usd_container = soup.find(id="dolar")
        usd_value = (
            usd_container.text.replace("\n", "").replace("USD", "").replace(",", ".").strip()
        )

        eur_container = soup.find(id="euro")
        eur_value = (
            eur_container.text.replace("\n", "").replace("EUR", "").replace(",", ".").strip()
        )

        cny_container = soup.find(id="yuan")
        cny_value = (
            cny_container.text.replace("\n", "").replace("CNY", "").replace(",", ".").strip()
        )

        rub_container = soup.find(id="rublo")
        rub_value = (
            rub_container.text.replace("\n", "").replace("RUB", "").replace(",", ".").strip()
        )

        try_container = soup.find(id="lira")
        try_value = (
            try_container.text.replace("\n", "").replace("TRY", "").replace(",", ".").strip()
        )
        return ({
            "USD": float(usd_value),
            "EUR": float(eur_value),
            "CNY": float(cny_value),
            "RUB": float(rub_value),
            "TRY": float(try_value),
        }, current_date)
    except Exception as e:
        _logger.error(e)
        return (1, False)
