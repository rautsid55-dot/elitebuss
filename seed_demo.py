import os, django
from decimal import Decimal
# Connect to the LIVE Neon Database
os.environ["DATABASE_URL"] = "postgres://neondb_owner:npg_clhzKZJdp1j5@ep-soft-frost-b3xw5hh6-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elitebuss_final.settings')
django.setup()

from core.models import CustomUser, Wallet, Transaction, Course, Purchase

# 1. Get demo user and add money
demo = CustomUser.objects.get(username='demo')
wallet, _ = Wallet.objects.get_or_create(user=demo)
wallet.balance = Decimal('500.00')
wallet.save()

# 2. Add a fake transaction history
Transaction.objects.create(
    wallet=wallet, amount=Decimal('500.00'), transaction_type='Referral',
    description="Bonus: Welcome to EliteBuss testing!"
)

# 3. Create a fake referred user to show in the history
fake_user, created = CustomUser.objects.get_or_create(
    username='test_buyer', 
    defaults={'email': 'test_buyer@gmail.com', 'referred_by': demo}
)
if created:
    fake_user.set_password('test123')
    fake_user.save()
    Wallet.objects.create(user=fake_user)

# 4. Create a fake purchase so the referral counts
course = Course.objects.first()
if course:
    Purchase.objects.get_or_create(
        user=fake_user, course=course, defaults={'status': 'Success'}
    )

print("\n✅ SUCCESS!")
print(f"Demo Wallet Balance: ₹{wallet.balance}")
print("Created fake referral user: test_buyer")