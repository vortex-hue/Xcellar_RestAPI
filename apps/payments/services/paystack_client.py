import requests
import logging
from decimal import Decimal
from django.conf import settings

logger = logging.getLogger(__name__)


class PaystackClient:
    """
    Paystack API client for handling payment operations.
    """
    
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.public_key = settings.PAYSTACK_PUBLIC_KEY
        self.base_url = 'https://api.paystack.co'
        self.headers = {
            'Authorization': f'Bearer {self.secret_key}',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request to Paystack API"""
        if not self.secret_key:
            logger.error("Paystack secret key not configured")
            return {'status': False, 'message': 'Paystack secret key not configured'}
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=self.headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Parse response
            try:
                response_data = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response from Paystack: {response.text}")
                return {'status': False, 'message': 'Invalid response from Paystack'}
            
            # Log error responses for debugging
            if not response_data.get('status', False):
                error_message = response_data.get('message', 'Unknown error')
                logger.error(f"Paystack API error ({endpoint}): {error_message}. Response: {response_data}")
            
            # Always return the response (even if status is False)
            # This allows the caller to handle errors appropriately
            return response_data
            
        except requests.exceptions.Timeout:
            logger.error(f"Paystack API timeout: {endpoint}")
            return {'status': False, 'message': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            logger.error(f"Paystack API error ({endpoint}): {e}")
            # Try to return error response if available
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_response = e.response.json()
                    logger.error(f"Paystack error response: {error_response}")
                    return error_response
                except (ValueError, AttributeError):
                    pass
            return {'status': False, 'message': str(e)}
    
    def initialize_transaction(self, email, amount, reference=None, callback_url=None, metadata=None):
        """
        Initialize a transaction.
        
        Args:
            email: Customer email
            amount: Amount in NGN (will be converted to kobo)
            reference: Transaction reference (optional)
            callback_url: Callback URL after payment (optional)
            metadata: Additional metadata (optional)
        
        Returns:
            dict: Paystack response with authorization_url
        """
        # Validate amount
        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal <= 0:
                return {'status': False, 'message': 'Amount must be greater than 0'}
        except (ValueError, TypeError):
            return {'status': False, 'message': 'Invalid amount'}
        
        data = {
            'email': email,
            'amount': int(amount_decimal * 100),  # Convert to kobo
        }
        
        if reference:
            data['reference'] = reference
        if callback_url:
            data['callback_url'] = callback_url
        if metadata:
            data['metadata'] = metadata
        
        return self._make_request('POST', '/transaction/initialize', data=data)
    
    def verify_transaction(self, reference):
        """
        Verify a transaction by reference.
        
        Args:
            reference: Transaction reference
        
        Returns:
            dict: Transaction details
        """
        return self._make_request('GET', f'/transaction/verify/{reference}')
    
    def create_customer(self, email, first_name=None, last_name=None, phone=None, metadata=None):
        """
        Create a Paystack customer.
        
        Args:
            email: Customer email
            first_name: First name (optional)
            last_name: Last name (optional)
            phone: Phone number (optional)
            metadata: Additional metadata (optional)
        
        Returns:
            dict: Customer details with customer_code
        """
        data = {'email': email}
        
        if first_name:
            data['first_name'] = first_name
        if last_name:
            data['last_name'] = last_name
        if phone:
            data['phone'] = phone
        if metadata:
            data['metadata'] = metadata
        
        return self._make_request('POST', '/customer', data=data)
    
    def assign_dedicated_account(self, customer_code, email=None, preferred_bank=None, first_name=None, last_name=None, phone=None):
        """
        Assign a dedicated virtual account to a customer (single-step).
        
        Args:
            customer_code: Paystack customer code
            email: Customer email (required for single-step)
            preferred_bank: Preferred bank code (optional)
            first_name: First name (optional)
            last_name: Last name (optional)
            phone: Phone number (optional)
        
        Returns:
            dict: DVA details
        """
        # For single-step, we need to pass customer_code and email
        data = {
            'customer': customer_code,
        }
        
        # Email is required for single-step DVA assignment
        if email:
            data['email'] = email
        
        if preferred_bank:
            data['preferred_bank'] = preferred_bank
        
        if first_name:
            data['first_name'] = first_name
        if last_name:
            data['last_name'] = last_name
        if phone:
            data['phone'] = phone
        
        return self._make_request('POST', '/dedicated_account/assign', data=data)
    
    def create_transfer_recipient(self, type, name, account_number, bank_code=None, currency='NGN'):
        """
        Create a transfer recipient.
        
        Args:
            type: Recipient type (nuban, mobile_money, basa)
            name: Recipient name
            account_number: Account number
            bank_code: Bank code (required for nuban)
            currency: Currency code (default: NGN)
        
        Returns:
            dict: Recipient details with recipient_code
        """
        data = {
            'type': type,
            'name': name,
            'account_number': account_number,
            'currency': currency,
        }
        
        if bank_code:
            data['bank_code'] = bank_code
        
        return self._make_request('POST', '/transferrecipient', data=data)
    
    def create_transfer(self, source, amount, recipient, reason=None, reference=None, currency='NGN'):
        """
        Create a transfer.
        
        Args:
            source: Balance source (balance)
            amount: Amount in NGN (will be converted to kobo)
            recipient: Recipient code
            reason: Transfer reason (optional)
            reference: Transfer reference (optional)
            currency: Currency code (default: NGN)
        
        Returns:
            dict: Transfer details
        """
        # Validate amount
        try:
            amount_decimal = Decimal(str(amount))
            if amount_decimal <= 0:
                return {'status': False, 'message': 'Amount must be greater than 0'}
        except (ValueError, TypeError):
            return {'status': False, 'message': 'Invalid amount'}
        
        data = {
            'source': source,
            'amount': int(amount_decimal * 100),  # Convert to kobo
            'recipient': recipient,
            'currency': currency,
        }
        
        if reason:
            data['reason'] = reason
        if reference:
            data['reference'] = reference
        
        return self._make_request('POST', '/transfer', data=data)
    
    def finalize_transfer(self, transfer_code, otp):
        """
        Finalize a transfer with OTP.
        
        Args:
            transfer_code: Transfer code
            otp: OTP code
        
        Returns:
            dict: Transfer details
        """
        data = {
            'transfer_code': transfer_code,
            'otp': otp,
        }
        
        return self._make_request('POST', '/transfer/finalize_transfer', data=data)
    
    def verify_transfer(self, reference):
        """
        Verify a transfer by reference.
        
        Args:
            reference: Transfer reference
        
        Returns:
            dict: Transfer details
        """
        return self._make_request('GET', f'/transfer/verify/{reference}')
    
    def get_transfer(self, transfer_code):
        """
        Get transfer details by code.
        
        Args:
            transfer_code: Transfer code
        
        Returns:
            dict: Transfer details
        """
        return self._make_request('GET', f'/transfer/{transfer_code}')
    
    def list_transfers(self, page=1, per_page=50, status=None, recipient=None):
        """
        List transfers.
        
        Args:
            page: Page number
            per_page: Items per page
            status: Filter by status (optional)
            recipient: Filter by recipient code (optional)
        
        Returns:
            dict: List of transfers
        """
        params = {
            'page': page,
            'perPage': per_page,
        }
        
        if status:
            params['status'] = status
        if recipient:
            params['recipient'] = recipient
        
        return self._make_request('GET', '/transfer', params=params)
    
    def list_banks(self, country='nigeria'):
        """
        List supported banks.
        
        Args:
            country: Country code (default: nigeria)
        
        Returns:
            dict: List of banks
        """
        return self._make_request('GET', '/bank', params={'country': country})

