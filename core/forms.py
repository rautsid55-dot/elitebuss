from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser

class SignUpForm(UserCreationForm):
    referred_by = forms.CharField(required=False, widget=forms.HiddenInput())
    
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove help texts that clutter the UI
        self.fields['username'].help_text = None
        self.fields['password2'].help_text = None
        # Remove validators to allow ANY character (including #)
        self.fields['username'].validators = []

class LoginForm(AuthenticationForm):
    pass