import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elitebuss_final.settings')
django.setup()
from core.models import CustomUser

for user in CustomUser.objects.all():
    user.email = 'rautsiddharthsiddharth9@gmail.com'
    user.save()
print("✅ All user emails set to rautsiddharthsiddharth9@gmail.com")