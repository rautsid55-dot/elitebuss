import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elitebuss_final.settings')
django.setup()
from core.models import CustomUser

print("\n--- ALL USERS IN DATABASE ---")
for u in CustomUser.objects.all():
    print(f"Username: {u.username} | Email: {u.email}")

# Reset password for rkraut if it exists
user = CustomUser.objects.filter(username='rkraut').first()
if user:
    user.set_password('rkraut123')
    user.save()
    print("\n✅ Found 'rkraut'! Password has been reset to: rkraut123")
else:
    print("\n⚠️ 'rkraut' does not exist in the database.")