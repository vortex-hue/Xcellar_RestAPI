from decimal import Decimal
from django.db.models import F
import logging

logger = logging.getLogger(__name__)


def get_user_profile(user):
    if user.user_type == 'USER':
        return user.user_profile
    elif user.user_type == 'COURIER':
        return user.courier_profile
    return None


def get_user_balance(user):
    profile = get_user_profile(user)
    return profile.balance if profile else Decimal('0.00')


def deduct_balance(user, amount, reference):
    profile = get_user_profile(user)
    if not profile:
        logger.error(f"Profile not found for user {user.email}")
        return False
    
    profile.refresh_from_db()
    if profile.balance < amount:
        logger.warning(f"Insufficient balance for {user.email}: {profile.balance} < {amount}")
        return False
    
    updated = profile.__class__.objects.filter(
        pk=profile.pk,
        balance__gte=amount
    ).update(
        balance=F('balance') - Decimal(str(amount)).quantize(Decimal('0.01'))
    )
    
    if updated == 0:
        logger.warning(f"Balance deduction failed for {user.email}: insufficient balance")
        return False
    
    profile.refresh_from_db()
    logger.info(f"Balance deducted for {user.email}: -₦{amount:,.2f} (Reference: {reference})")
    return True


def add_balance(user, amount, reference):
    profile = get_user_profile(user)
    if not profile:
        return False
    
    profile.__class__.objects.filter(pk=profile.pk).update(
        balance=F('balance') + Decimal(str(amount)).quantize(Decimal('0.01'))
    )
    profile.refresh_from_db()
    logger.info(f"Balance added for {user.email}: +₦{amount:,.2f} (Reference: {reference})")
    return True

