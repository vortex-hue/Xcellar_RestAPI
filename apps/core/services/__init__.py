import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class PaystackAccountVerification:
    """
    Paystack Account Verification Service for resolving bank account details.
    """
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = 'https://api.paystack.co'
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def resolve_account(self, account_number, bank_code):
        """
        Resolve bank account details.
        
        Args:
            account_number: Bank account number
            bank_code: Bank code
        
        Returns:
            dict: Account details with account_name and bank_id
                {
                    "status": true,
                    "message": "Account number resolved",
                    "data": {
                        "account_number": "8115333313",
                        "account_name": "PETER BENJAMIN ANI",
                        "bank_id": 171
                    }
                }
        """
        url = f"{self.base_url}/bank/resolve"
        params = {
            'account_number': account_number,
            'bank_code': bank_code,
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack account verification error: {e}")
            if hasattr(e.response, 'json'):
                return e.response.json()
            raise

