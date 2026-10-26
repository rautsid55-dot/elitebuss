import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elitebuss_final.settings')
django.setup()
from core.models import CustomUser

# Create Demo User
if not CustomUser.objects.filter(username='demo').exists():
    u = CustomUser.objects.create_user('demo', 'demo@elitebuss.com', 'demo123')
    u.save()
    print("Demo user created: username='demo', password='demo123'")