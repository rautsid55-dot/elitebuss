import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elitebuss_final.settings')
django.setup()
from core.models import CustomUser, Wallet, SiteSetting

# Create wallets for existing users
for u in CustomUser.objects.all():
    Wallet.objects.get_or_create(user=u)

# Create default Site Settings
SiteSetting.load()
print("✅ Wallets and Settings created.")