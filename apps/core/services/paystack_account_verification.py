import requests
import logging
import json
import os
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
        # Load Nigerian banks data
        self._load_banks_data()
    
    def _load_banks_data(self):
        """Load Nigerian banks data from JSON file"""
        try:
            file_path = os.path.join(os.path.dirname(__file__), 'nigerian_banks.json')
            with open(file_path, 'r', encoding='utf-8') as f:
                self.banks_data = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load banks data file: {e}")
            self.banks_data = []
    
    def get_banks(self):
        """
        Get list of Nigerian banks.
        
        Returns:
            list: List of banks with code and name
        """
        # Try to fetch from Paystack API first (more up-to-date)
        # Note: Paystack bank list endpoint doesn't require authentication
        if self.secret_key:
            try:
                response = self._fetch_banks_from_paystack()
                if response and response.get('status'):
                    return response.get('data', [])
            except Exception as e:
                logger.warning(f"Failed to fetch banks from Paystack API: {e}")
        else:
            # Try without authentication (public endpoint)
            try:
                url = f"{self.base_url}/bank?country=nigeria"
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get('status'):
                        return response_data.get('data', [])
            except Exception as e:
                logger.warning(f"Failed to fetch banks from Paystack API (public): {e}")
        
        # Fallback to local data
        return self.banks_data
    
    def _fetch_banks_from_paystack(self):
        """Fetch banks list from Paystack API"""
        try:
            url = f"{self.base_url}/bank?country=nigeria"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching banks from Paystack: {e}")
            return None
    
    def get_bank_code_by_name(self, bank_name):
        """
        Get bank code by bank name (case-insensitive search).
        Supports exact match and partial match.
        
        Args:
            bank_name: Bank name to search for
        
        Returns:
            str: Bank code if found, None otherwise
        """
        if not bank_name:
            return None
        
        bank_name_lower = bank_name.lower().strip()
        
        # First, try exact match in local data
        for bank in self.banks_data:
            if bank.get('name', '').lower() == bank_name_lower:
                return str(bank.get('code', ''))
        
        # Try Paystack API if available (more up-to-date)
        if self.secret_key:
            try:
                banks = self._fetch_banks_from_paystack()
                if banks and banks.get('status'):
                    for bank in banks.get('data', []):
                        bank_api_name = bank.get('name', '').lower()
                        if bank_name_lower == bank_api_name:
                            # Paystack API uses 'id' as bank code
                            return str(bank.get('id', bank.get('code', '')))
            except Exception as e:
                logger.warning(f"Error searching bank in Paystack API: {e}")
        
        # Try partial match (contains) in local data
        for bank in self.banks_data:
            bank_local_name = bank.get('name', '').lower()
            if bank_name_lower in bank_local_name or bank_local_name in bank_name_lower:
                return str(bank.get('code', ''))
        
        # Try partial match in Paystack API if available
        if self.secret_key:
            try:
                banks = self._fetch_banks_from_paystack()
                if banks and banks.get('status'):
                    for bank in banks.get('data', []):
                        bank_api_name = bank.get('name', '').lower()
                        if bank_name_lower in bank_api_name or bank_api_name in bank_name_lower:
                            # Paystack API uses 'id' as bank code
                            return str(bank.get('id', bank.get('code', '')))
            except Exception as e:
                logger.warning(f"Error searching bank in Paystack API: {e}")
        
        return None
    
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
        if not self.secret_key:
            logger.error("Paystack secret key not configured")
            return {'status': False, 'message': 'Paystack secret key not configured'}
        
        url = f"{self.base_url}/bank/resolve"
        params = {
            'account_number': account_number,
            'bank_code': bank_code,
        }
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            logger.error(f"Paystack account verification timeout")
            return {'status': False, 'message': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack account verification error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    return e.response.json()
                except:
                    pass
            return {'status': False, 'message': str(e)}

