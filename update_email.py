import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elitebuss_final.settings')
django.setup()
from core.models import CustomUser

# Update Demo User
demo_user = CustomUser.objects.filter(username='demo').first()
if demo_user:
    demo_user.email = 'rautsiddharthsiddharth9@gmail.com'
    demo_user.save()
    print("✅ Demo user email updated to: rautsiddharthsiddharth9@gmail.com")

# Update Owner User (just in case you test on the owner account too)
owner_user = CustomUser.objects.filter(username='owner').first()
if owner_user:
    owner_user.email = 'rautsiddharthsiddharth9@gmail.com'
    owner_user.save()
    print("✅ Owner user email updated to: rautsiddharthsiddharth9@gmail.com")