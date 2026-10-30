import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elitebuss_final.settings')
django.setup()
from core.models import CustomUser
from django.utils.crypto import get_random_string

for user in CustomUser.objects.all():
    if not user.referral_code:
        user.referral_code = get_random_string(10).upper()
        user.save()
        print(f"✅ Generated code for {user.username}: {user.referral_code}")