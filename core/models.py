from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class SiteSetting(models.Model):
    razorpay_key_id = models.CharField(max_length=150, blank=True, null=True)
    razorpay_key_secret = models.CharField(max_length=150, blank=True, null=True)
    razorpay_webhook_secret = models.CharField(max_length=150, blank=True, null=True)
    referral_commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super(SiteSetting, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class CustomUser(AbstractUser):
    is_owner = models.BooleanField(default=False)
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = str(uuid.uuid4()).replace('-', '')[:10].upper()
        super().save(*args, **kwargs)

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    thumbnail_url = models.URLField()
    video_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Purchase(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    razorpay_order_id = models.CharField(max_length=100)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(max_length=20, default='Pending') # Pending, Success
    created_at = models.DateTimeField(auto_now_add=True)

class ReferralEarning(models.Model):
    referrer = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

class ActiveDevice(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='devices')
    session_key = models.CharField(max_length=40)
    device_name = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_active = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.device_name}"