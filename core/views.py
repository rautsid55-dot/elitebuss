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
from django.conf import settings
from .models import *
from .forms import SignUpForm, LoginForm
from django.views.decorators.csrf import csrf_exempt

def verify_signature(order_id, payment_id, signature, secret):
    msg = f"{order_id}|{payment_id}"
    generated_signature = hmac.new(secret.encode('utf-8'), msg.encode('utf-8'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(generated_signature, signature)

def index(request):
    courses = Course.objects.all().order_by('-created_at')[:3]
    site_settings = SiteSetting.load()
    return render(request, 'core/index.html', {'courses': courses, 'settings': site_settings})

@login_required
def my_learning(request):
    purchases = Purchase.objects.filter(user=request.user, status='Success')
    purchased_courses = [p.course for p in purchases]
    return render(request, 'core/my_learning.html', {'courses': purchased_courses})

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
            Wallet.objects.create(user=user) # Create wallet on signup
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

def terms_view(request):
    return render(request, 'core/legal.html', {'title': 'Terms & Conditions', 'content': '<h3>1. Acceptance</h3><p>By using EliteBuss, you agree to these terms.</p><h3>2. Content</h3><p>All courses are for personal use only and cannot be resold.</p>'})

def privacy_view(request):
    return render(request, 'core/legal.html', {'title': 'Privacy Policy', 'content': '<h3>1. Data Collection</h3><p>We collect your email and IP address for security purposes.</p><h3>2. Referrals</h3><p>We track referral IPs to prevent fraud.</p>'})

def refund_view(request):
    return render(request, 'core/legal.html', {'title': 'Refund Policy', 'content': '<h3>1. Refunds</h3><p>Due to the digital nature of courses, we do not offer refunds once the course is unlocked.</p>'})

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def affiliate_view(request):
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    referrals = ReferralEarning.objects.filter(referrer=request.user).order_by('-created_at') if hasattr(request.user, 'referralearning_set') else []
    
    # Get referrals based on user.referrals (CustomUser logic)
    my_referrals = CustomUser.objects.filter(referred_by=request.user)
    referrals_count = my_referrals.count()
    transactions = wallet.transactions.all().order_by('-created_at')
    withdrawals = WithdrawalRequest.objects.filter(user=request.user).order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'request_withdrawal':
            amount = Decimal(request.POST.get('amount', '0'))
            method = request.POST.get('method')
            details = request.POST.get('details')
            
            if amount > wallet.balance:
                messages.error(request, 'Insufficient balance.')
            elif amount < 100:
                messages.error(request, 'Minimum withdrawal is Ã¢â€šÂ¹100.')
            else:
                WithdrawalRequest.objects.create(user=request.user, amount=amount, payment_method=method, payment_details=details)
                messages.success(request, 'Withdrawal request submitted successfully! Awaiting admin approval.')
                # Send notification
                Notification.objects.create(user=request.user, title="Withdrawal Requested", message=f"Your withdrawal of Ã¢â€šÂ¹{amount} is pending.")
                return redirect('affiliate')

    return render(request, 'core/affiliate.html', {
        'wallet': wallet, 'my_referrals': my_referrals, 'referrals_count': referrals_count,
        'transactions': transactions, 'withdrawals': withdrawals
    })

@login_required
def settings_view(request):
    if not ActiveDevice.objects.filter(session_key=request.session.session_key).exists():
        device_name = request.META.get('HTTP_USER_AGENT', 'Unknown Device')[:50]
        ActiveDevice.objects.create(user=request.user, session_key=request.session.session_key, device_name=device_name, ip_address=request.META.get('REMOTE_ADDR'))

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            request.user.username = request.POST.get('username')
            request.user.email = request.POST.get('email')
            request.user.save()
            messages.success(request, 'Profile updated successfully!')
        elif action == 'change_password':
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            if new_password == confirm_password and len(new_password) >= 6:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(request, 'Password changed successfully!')
            else:
                messages.error(request, 'Passwords do not match or are too short.')
            return redirect('settings')
        elif action == 'logout_device':
            device = ActiveDevice.objects.filter(id=request.POST.get('device_id'), user=request.user).first()
            if device: device.delete()
            messages.success(request, 'Device logged out.')
            return redirect('settings')

    devices = ActiveDevice.objects.filter(user=request.user).order_by('-last_active')
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False)
    return render(request, 'core/settings.html', {'devices': devices, 'notifications': unread_notifications})

@login_required
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    has_purchased = Purchase.objects.filter(user=request.user, course=course, status='Success').exists() or request.user.is_owner
    settings_obj = SiteSetting.load()
    
    # SECURITY: Do not pass video_url to template unless purchased
    context = {'course': course, 'has_purchased': has_purchased}
    
    # Coupon Logic
    final_price = course.price
    discount_percent = 0
    coupon_code = request.GET.get('coupon', '')
    if coupon_code:
        coupon = Coupon.objects.filter(code=coupon_code, is_active=True).first()
        if coupon:
            discount_percent = coupon.discount_percentage
            final_price = course.price - (course.price * Decimal(discount_percent) / Decimal('100.0'))
            messages.success(request, f'Coupon applied! {discount_percent}% off.')
        else:
            messages.error(request, 'Invalid or expired coupon.')
    
    context['final_price'] = final_price
    context['discount_percent'] = discount_percent

    if not has_purchased:
        if request.user.username == 'demo':
            Purchase.objects.create(user=request.user, course=course, status='Success')
            messages.success(request, 'Demo Payment Successful!')
            return redirect('course_detail', course_id=course.id)
            
        if not settings_obj.razorpay_key_id or not settings_obj.razorpay_key_secret:
            context['payment_disabled'] = True
        else:
            context['payment_disabled'] = False
            order_amount = int(final_price * 100)
            auth = (settings_obj.razorpay_key_id, settings_obj.razorpay_key_secret)
            payload = {'amount': order_amount, 'currency': 'INR', 'payment_capture': 1}
            try:
                response = requests.post("https://api.razorpay.com/v1/orders", auth=auth, json=payload, timeout=10)
                if response.status_code == 200:
                    razorpay_order = response.json()
                    Purchase.objects.create(user=request.user, course=course, razorpay_order_id=razorpay_order['id'], status='Pending', discount_applied=discount_percent)
                    context['razorpay_order_id'] = razorpay_order['id']
                    context['razorpay_merchant_key'] = settings_obj.razorpay_key_id
                    context['order_amount'] = order_amount
                else:
                    context['payment_disabled'] = True
            except Exception:
                context['payment_disabled'] = True
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
                
                # REAL REFERRAL LOGIC
                if purchase.user.referred_by:
                    commission = (purchase.course.price * settings_obj.referral_commission_percentage) / Decimal('100.0')
                    referrer_wallet, _ = Wallet.objects.get_or_create(user=purchase.user.referred_by)
                    referrer_wallet.balance += commission
                    referrer_wallet.save()
                    
                    Transaction.objects.create(
                        wallet=referrer_wallet, amount=commission, transaction_type='Referral',
                        description=f"Commission from {purchase.user.username}'s purchase of {purchase.course.title}"
                    )
                    Notification.objects.create(user=purchase.user.referred_by, title="Referral Earning!", message=f"You earned Ã¢â€šÂ¹{commission} from {purchase.user.username}'s purchase.")
                
                messages.success(request, 'Payment verified! Access granted.')
                return redirect('course_detail', course_id=purchase.course.id)
        return redirect('index')
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
            site_settings.hero_title = request.POST.get('hero_title')
            site_settings.hero_description = request.POST.get('hero_description')
            try: site_settings.referral_commission_percentage = Decimal(request.POST.get('commission', '10'))
            except: pass
            site_settings.save()
            messages.success(request, 'Settings saved!')
        elif action == 'add_course':
            Course.objects.create(
                title=request.POST.get('title'), description=request.POST.get('description'),
                price=Decimal(request.POST.get('price')), thumbnail_url=request.POST.get('thumbnail_url'), video_url=request.POST.get('video_url')
            )
            messages.success(request, 'Course added!')
        elif action == 'delete_course':
            Course.objects.filter(id=request.POST.get('course_id')).delete()
        elif action == 'approve_withdrawal':
            wr = WithdrawalRequest.objects.get(id=request.POST.get('withdrawal_id'))
            if wr.status == 'Pending':
                wallet = wr.user.wallet
                if wallet.balance >= wr.amount:
                    wallet.balance -= wr.amount
                    wallet.save()
                    wr.status = 'Approved'
                    wr.save()
                    Transaction.objects.create(wallet=wallet, amount=-wr.amount, transaction_type='Withdrawal', description=f"Withdrawal to {wr.payment_method} ({wr.payment_details})")
                    Notification.objects.create(user=wr.user, title="Withdrawal Approved!", message=f"Your withdrawal of Ã¢â€šÂ¹{wr.amount} was approved and sent.")
                    messages.success(request, f'Approved withdrawal for {wr.user.username}.')
                else:
                    messages.error(request, 'User has insufficient balance.')
        elif action == 'reject_withdrawal':
            wr = WithdrawalRequest.objects.get(id=request.POST.get('withdrawal_id'))
            wr.status = 'Rejected'
            wr.save()
            Notification.objects.create(user=wr.user, title="Withdrawal Rejected", message=f"Your withdrawal of Ã¢â€šÂ¹{wr.amount} was rejected. Please contact support.")
            messages.success(request, 'Withdrawal rejected.')
        elif action == 'send_notification':
            user = CustomUser.objects.get(id=request.POST.get('user_id'))
            Notification.objects.create(user=user, title=request.POST.get('title'), message=request.POST.get('message'))
            messages.success(request, 'Notification sent!')
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_coupon':
            Coupon.objects.create(code=request.POST.get('code').upper(), discount_percentage=request.POST.get('discount'))
            messages.success(request, 'Coupon created!')
            return redirect('dashboard')
        elif action == 'ban_user':
            user = CustomUser.objects.get(id=request.POST.get('user_id'))
            user.is_banned = not user.is_banned
            user.save()
            messages.success(request, 'User ban status updated.')
            return redirect('dashboard')
            
    users = CustomUser.objects.all().order_by('-date_joined')
    courses = Course.objects.all().order_by('-created_at')
    purchases = Purchase.objects.filter(status='Success')
    withdrawals = WithdrawalRequest.objects.all().order_by('-created_at')
    alerts = SecurityAlert.objects.filter(is_resolved=False).order_by('-created_at')
    coupons = Coupon.objects.all()
    total_revenue = sum(p.course.price for p in purchases)
    
    return render(request, 'core/dashboard.html', {
        'users': users, 'courses': courses, 'total_revenue': total_revenue,
        'purchases_count': purchases.count(), 'withdrawals': withdrawals, 
        'settings': site_settings, 'alerts': alerts, 'coupons': coupons
    })

@login_required
def mark_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'index'))