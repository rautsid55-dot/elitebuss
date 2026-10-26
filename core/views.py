import json
import requests
import hmac
import hashlib
import random
import string
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponse
from django.utils import timezone
from django.conf import settings
from .models import Course, Purchase, CustomUser, ReferralEarning, SiteSetting, ActiveDevice
from .forms import SignUpForm, LoginForm
from django.views.decorators.csrf import csrf_exempt
import resend

def verify_signature(order_id, payment_id, signature, secret):
    msg = f"{order_id}|{payment_id}"
    generated_signature = hmac.new(secret.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated_signature, signature)

def index(request):
    courses = Course.objects.all().order_by('-created_at')[:3]
    return render(request, 'core/index.html', {'courses': courses})

def courses_view(request):
    courses = Course.objects.all().order_by('-created_at')
    return render(request, 'core/courses.html', {'courses': courses})

def signup_view(request):
    ref_code = request.GET.get('ref', '')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            referred_by_code = request.POST.get('referred_by')
            if referred_by_code:
                referrer = CustomUser.objects.filter(referral_code=referred_by_code).first()
                if referrer: user.referred_by = referrer
            user.save()
            login(request, user)
            return redirect('index')
        else:
            return render(request, 'core/signup.html', {'form': form, 'ref_code': ref_code})
    else:
        form = SignUpForm(initial={'referred_by': ref_code})
    return render(request, 'core/signup.html', {'form': form, 'ref_code': ref_code})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('dashboard' if user.is_owner else 'index')
    else:
        form = LoginForm()
    return render(request, 'core/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def affiliate_view(request):
    referrals = ReferralEarning.objects.filter(referrer=request.user).order_by('-created_at')
    total_earnings = sum(r.amount for r in referrals)
    return render(request, 'core/affiliate.html', {'referrals': referrals, 'total_earnings': total_earnings})

@login_required
def settings_view(request):
    if not ActiveDevice.objects.filter(session_key=request.session.session_key).exists():
        device_name = request.META.get('HTTP_USER_AGENT', 'Unknown Device')[:50]
        ActiveDevice.objects.create(
            user=request.user, session_key=request.session.session_key,
            device_name=device_name, ip_address=request.META.get('REMOTE_ADDR')
        )

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            request.user.username = request.POST.get('username')
            request.user.email = request.POST.get('email')
            request.user.save()
            messages.success(request, 'Profile updated successfully!')
        
        elif action == 'request_otp':
            otp = ''.join(random.choices(string.digits, k=6))
            request.session['password_reset_otp'] = otp
            
            subject = 'Your EliteBuss Password Reset OTP'
            message = f'Hello {request.user.username},\n\nYour 6-digit OTP to change your password is:\n\n{otp}\n\nIf you did not request this, please ignore this email.\n\nThanks,\nEliteBuss Team'
            
            try:
                resend.api_key = settings.RESEND_API_KEY
                # Send to the exact email of the logged-in user
                recipient = request.user.email
                params = {
                    "from": "EliteBuss <onboarding@resend.dev>",
                    "to": [recipient],
                    "subject": subject,
                    "text": message
                }
                resend.Emails.send(params)
                messages.success(request, f'OTP sent successfully to {recipient}!')
            except Exception as e:
                messages.error(request, f'Email API Error: {str(e)}')
            return redirect('settings')
            
        elif action == 'verify_otp':
            entered_otp = request.POST.get('otp')
            if entered_otp == request.session.get('password_reset_otp'):
                new_password = request.POST.get('new_password')
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                del request.session['password_reset_otp']
                messages.success(request, 'Password changed successfully!')
            else:
                messages.error(request, 'Invalid OTP. Try again.')
            return redirect('settings')
            
        elif action == 'logout_device':
            device_id = request.POST.get('device_id')
            device = ActiveDevice.objects.filter(id=device_id, user=request.user).first()
            if device:
                device.delete()
                messages.success(request, 'Device logged out.')
            return redirect('settings')

    devices = ActiveDevice.objects.filter(user=request.user).order_by('-last_active')
    return render(request, 'core/settings.html', {'devices': devices})

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    has_purchased = Purchase.objects.filter(user=request.user, course=course, status='Success').exists() or request.user.is_owner
    settings_obj = SiteSetting.load()
    context = {'course': course, 'has_purchased': has_purchased}

    if not has_purchased:
        if request.user.username == 'demo':
            Purchase.objects.create(user=request.user, course=course, status='Success')
            messages.success(request, 'Demo Payment Successful! Access granted.')
            return redirect('course_detail', course_id=course.id)
            
        if not settings_obj.razorpay_key_id or not settings_obj.razorpay_key_secret:
            context['payment_disabled'] = True
        else:
            context['payment_disabled'] = False
            order_amount = int(course.price * 100)
            auth = (settings_obj.razorpay_key_id, settings_obj.razorpay_key_secret)
            payload = {'amount': order_amount, 'currency': 'INR', 'payment_capture': 1}
            try:
                response = requests.post("https://api.razorpay.com/v1/orders", auth=auth, json=payload, timeout=10)
                if response.status_code == 200:
                    razorpay_order = response.json()
                    Purchase.objects.create(user=request.user, course=course, razorpay_order_id=razorpay_order['id'], status='Pending')
                    context['razorpay_order_id'] = razorpay_order['id']
                    context['razorpay_merchant_key'] = settings_obj.razorpay_key_id
                    context['order_amount'] = order_amount
                else:
                    context['payment_disabled'] = True
                    messages.error(request, "Gateway awaiting valid live/test Razorpay keys.")
            except Exception:
                context['payment_disabled'] = True
                messages.error(request, "Network error reaching payment gateway.")

    return render(request, 'core/course_detail.html', context)

@csrf_exempt
def payment_verify(request):
    if request.method == "POST":
        payment_id = request.POST.get('razorpay_payment_id', '')
        razorpay_order_id = request.POST.get('razorpay_order_id', '')
        signature = request.POST.get('razorpay_signature', '')
        settings_obj = SiteSetting.load()
        if not settings_obj.razorpay_key_secret:
            return HttpResponseBadRequest("Payment keys missing.")
        if verify_signature(razorpay_order_id, payment_id, signature, settings_obj.razorpay_key_secret):
            purchase = Purchase.objects.filter(razorpay_order_id=razorpay_order_id).first()
            if purchase and purchase.status != 'Success':
                purchase.razorpay_payment_id = payment_id
                purchase.razorpay_signature = signature
                purchase.status = 'Success'
                purchase.save()
                if purchase.user.referred_by:
                    commission = (purchase.course.price * settings_obj.referral_commission_percentage) / Decimal('100.0')
                    ReferralEarning.objects.create(referrer=purchase.user.referred_by, purchase=purchase, amount=commission)
                messages.success(request, 'Payment verified! You now have lifetime access.')
                return redirect('course_detail', course_id=purchase.course.id)
        messages.error(request, 'Payment verification failed.')
        return redirect('index')
    return HttpResponseBadRequest()

@csrf_exempt
def razorpay_webhook(request):
    if request.method == 'POST':
        settings_obj = SiteSetting.load()
        webhook_secret = settings_obj.razorpay_webhook_secret
        if not webhook_secret:
            return HttpResponse(status=400)
        webhook_signature = request.headers.get('X-Razorpay-Signature', '')
        payload = request.body.decode('utf-8')
        generated_sig = hmac.new(webhook_secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
        if hmac.compare_digest(generated_sig, webhook_signature):
            data = json.loads(payload)
            if data.get('event') == 'order.paid':
                order_id = data['payload']['order']['entity']['id']
                payment_id = data['payload']['payment']['entity']['id']
                purchase = Purchase.objects.filter(razorpay_order_id=order_id).first()
                if purchase and purchase.status != 'Success':
                    purchase.razorpay_payment_id = payment_id
                    purchase.status = 'Success'
                    purchase.save()
            return HttpResponse(status=200)
        return HttpResponse(status=400)
    return HttpResponseBadRequest()

@login_required
def dashboard(request):
    if not request.user.is_owner:
        return redirect('index')
    site_settings = SiteSetting.load()
    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'save_settings':
            site_settings.razorpay_key_id = request.POST.get('razorpay_key_id', '').strip()
            site_settings.razorpay_key_secret = request.POST.get('razorpay_key_secret', '').strip()
            site_settings.razorpay_webhook_secret = request.POST.get('razorpay_webhook_secret', '').strip()
            try: site_settings.referral_commission_percentage = Decimal(request.POST.get('commission', '10'))
            except: pass
            site_settings.save()
            messages.success(request, 'Razorpay & Referral settings saved!')
        elif action == 'add_course':
            title = request.POST.get('title', '').strip()
            price = request.POST.get('price', '0').strip()
            if title and price:
                Course.objects.create(
                    title=title, description=request.POST.get('description', '').strip(),
                    price=Decimal(price), thumbnail_url=request.POST.get('thumbnail_url', '').strip(),
                    video_url=request.POST.get('video_url', '').strip()
                )
                messages.success(request, f'Course "{title}" added!')
        elif action == 'delete_course':
            Course.objects.filter(id=request.POST.get('course_id')).delete()
            messages.success(request, 'Course removed.')
        return redirect('dashboard')

    users = CustomUser.objects.all()
    courses = Course.objects.all().order_by('-created_at')
    purchases = Purchase.objects.filter(status='Success')
    context = {
        'users': users, 'courses': courses,
        'total_revenue': sum(p.course.price for p in purchases),
        'purchases_count': purchases.count(),
        'referrals_paid': sum(r.amount for r in ReferralEarning.objects.all()),
        'settings': site_settings
    }
    return render(request, 'core/dashboard.html', context)