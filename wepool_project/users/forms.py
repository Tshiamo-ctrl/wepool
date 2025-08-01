# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Profile

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password1', 'password2']

class ProfileForm(forms.ModelForm):
    member_type = forms.ChoiceField(
        choices=[
            ('paying', 'Paying Member'),
            ('sponsored', 'PIF Member')  # UI display change
        ],
        widget=forms.RadioSelect,
        required=True,
        label="Membership Type"
    )

    # Terms and conditions checkbox
    agreed_to_terms = forms.BooleanField(
        required=True,
        label="I agree to the WePool Tribe Terms and Conditions",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # Communications opt-in
    communications_opt_in = forms.BooleanField(
        required=False,
        label="I agree to receive communications from WePool Tribe (recommended)",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    class Meta:
        model = Profile
        fields = [
            'phone', 'referrer_phone', 'member_type', 'date_of_birth',
            'city', 'state', 'country', 'zip_code',  # Removed 'address'
            'agreed_to_terms', 'communications_opt_in'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={
                'type': 'tel',
                'pattern': '[0-9]*',
                'inputmode': 'numeric',
                'class': 'form-control',
                'placeholder': 'Enter phone number (numbers only)',
                'title': 'Please enter numbers only'
            }),
            'referrer_phone': forms.TextInput(attrs={
                'type': 'tel',
                'pattern': '[0-9]*',
                'inputmode': 'numeric',
                'class': 'form-control',
                'placeholder': 'Referrer phone number (numbers only)',
                'title': 'Please enter numbers only'
            }),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City/Suburb'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Province'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP/Postal Code'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain only digits.")
        return phone

    def clean_referrer_phone(self):
        referrer_phone = self.cleaned_data.get('referrer_phone')
        if referrer_phone and not referrer_phone.isdigit():
            raise forms.ValidationError("Referrer phone number must contain only digits.")
        return referrer_phone

    def save(self, commit=True):
        profile = super().save(commit=False)
        if self.cleaned_data['agreed_to_terms']:
            profile.terms_agreed_date = timezone.now()
        if commit:
            profile.save()
        return profile

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'phone', 'date_of_birth', 'city', 'state', 'country', 'zip_code',  # Removed 'address'
            'communications_opt_in'
        ]
        widgets = {
            'phone': forms.TextInput(attrs={
                'type': 'tel',
                'pattern': '[0-9]*',
                'inputmode': 'numeric',
                'class': 'form-control',
                'readonly': True,  # Don't allow phone changes in profile update
                'title': 'Phone number cannot be changed'
            }),
            'date_of_birth': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City/Suburb'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State/Province'}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Country'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ZIP/Postal Code'}),
        }
