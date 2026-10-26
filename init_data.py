import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'elitebuss_final.settings')
django.setup()
from core.models import CustomUser, Course

if not CustomUser.objects.filter(username='owner').exists():
    u = CustomUser.objects.create_superuser('owner', 'owner@elitebuss.com', 'EliteAdmin@2026')
    u.is_owner = True
    u.save()

if not CustomUser.objects.filter(username='demo').exists():
    CustomUser.objects.create_user('demo', 'demo@elitebuss.com', 'demo123')

if not Course.objects.exists():
    Course.objects.create(
        title='EliteBuss Pro Business Mastery',
        description='Complete step-by-step training program with lifetime video access and resources.',
        price=999.00,
        thumbnail_url='https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=800',
        video_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    )