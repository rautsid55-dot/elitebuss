from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('courses/', views.courses_view, name='courses'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('affiliate/', views.affiliate_view, name='affiliate'),
    path('settings/', views.settings_view, name='settings'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('payment/verify/', views.payment_verify, name='payment_verify'),
    path('payment/webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    path('dashboard/', views.dashboard, name='dashboard'),
]