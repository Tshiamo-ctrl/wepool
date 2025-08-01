# users/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.http import JsonResponse
from django.utils import timezone
from .forms import UserRegistrationForm, ProfileForm, ProfileUpdateForm
from .models import Profile
from core.models import Referral
from core.utils import build_referral_matrix

def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = ProfileForm(request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            # Create user
            user = user_form.save(commit=False)
            user.is_active = False  # Require email verification
            user.save()

            # Update profile
            profile = user.profile
            profile_data = profile_form.cleaned_data
            for field, value in profile_data.items():
                setattr(profile, field, value)

            # Set terms agreement timestamp
            if profile_data.get('agreed_to_terms'):
                profile.terms_agreed_date = timezone.now()

            profile.save()

            # Create referral if referrer exists
            if profile.referrer_phone:
                try:
                    referrer_profile = Profile.objects.get(phone=profile.referrer_phone)
                    Referral.objects.create(referrer=referrer_profile, referred=profile)
                except Profile.DoesNotExist:
                    pass

            # Send verification email
            current_site = get_current_site(request)
            verification_url = f"http://{current_site.domain}{reverse('verify_email', args=[str(profile.email_verification_token)])}"

            send_mail(
                'Verify your WePool Tribe account',
                f'Welcome to WePool Tribe! Please click the following link to verify your email: {verification_url}',
                'noreply@wepooltribe.com',
                [user.email],
                fail_silently=False,
            )

            # Send admin notification
            send_mail(
                'New User Registration - WePool Tribe',
                f'A new user has registered: {user.get_full_name()} ({user.email})\nMember Type: {profile.get_member_type_display_ui()}\nPhone: {profile.phone}',
                'noreply@wepooltribe.com',
                ['admin@wepooltribe.com'],
                fail_silently=True,
            )

            messages.success(request, 'Registration successful! Please check your email to verify your account.')
            return redirect('login')
    else:
        user_form = UserRegistrationForm()
        profile_form = ProfileForm()

    return render(request, 'users/register.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

def verify_email(request, token):
    try:
        profile = Profile.objects.get(email_verification_token=token)
        profile.verified_email = True
        profile.user.is_active = True
        profile.user.save()
        profile.save()

        # Check Yellow qualification
        profile.check_yellow_qualification()

        messages.success(request, 'Email verified successfully! You can now log in.')
        return redirect('login')
    except Profile.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('login')

@login_required
def user_dashboard(request):
    profile = request.user.profile
    matrix = build_referral_matrix(profile)
    direct_referrals = Referral.objects.filter(referrer=profile).select_related('referred__user')

    return render(request, 'users/dashboard.html', {
        'profile': profile,
        'matrix': matrix,
        'direct_referrals': direct_referrals
    })

@login_required
def update_profile(request):
    profile = request.user.profile

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_dashboard')
    else:
        form = ProfileUpdateForm(instance=profile)

    return render(request, 'users/update_profile.html', {'form': form})

# users/views.py - Update the AJAX view
@login_required
def update_techconnect_status(request):
    """AJAX endpoint to update TAC Connector registration status"""
    if request.method == 'POST':
        profile = request.user.profile

        registered = request.POST.get('registered') == 'true'
        tacconnector_link = request.POST.get('tacconnector_link', '')

        # Use new field names
        profile.registered_tacconnector = registered  # Updated field name
        if tacconnector_link:
            profile.tacconnector_link = tacconnector_link  # Updated field name
        profile.save()

        # Check if now qualifies for yellow status
        qualified = profile.check_yellow_qualification()

        return JsonResponse({
            'success': True,
            'qualified_for_yellow': qualified,
            'new_status': profile.status
        })

    return JsonResponse({'success': False})

@login_required
def referral_tree_data(request):
    """Get referral tree data for visualization"""
    profile = request.user.profile

    def build_tree_node(profile):
        referrals = Referral.objects.filter(referrer=profile).select_related('referred__user')
        return {
            'name': profile.user.get_full_name(),
            'phone': profile.phone,
            'status': profile.status,
            'member_type': profile.member_type,
            'children': [build_tree_node(ref.referred) for ref in referrals[:10]]
        }

    tree_data = build_tree_node(profile)
    return JsonResponse(tree_data)

def check_referrer_exists(request):
    """AJAX endpoint to check if referrer phone exists"""
    phone = request.GET.get('phone', '')

    if phone:
        exists = Profile.objects.filter(phone=phone).exists()
        if exists:
            referrer = Profile.objects.get(phone=phone)
            return JsonResponse({
                'exists': True,
                'name': referrer.user.get_full_name(),
                'member_type': referrer.member_type
            })

    return JsonResponse({'exists': False})

# users/views.py - Update the verify_email function (continued)
def verify_email(request, token):
    try:
        profile = Profile.objects.get(email_verification_token=token)

        # Activate the user account
        profile.verified_email = True
        profile.user.is_active = True
        profile.user.save()
        profile.save()

        # Check Yellow qualification
        profile.check_yellow_qualification()

        messages.success(request, 'Email verified successfully! You can now log in.')
        return redirect('login')
    except Profile.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('login')

# Add this function to handle login debugging
from django.contrib.auth import authenticate
from django.views.decorators.http import require_http_methods

@require_http_methods(["POST"])
def debug_login(request):
    """Debug function to check login issues"""
    username = request.POST.get('username')
    password = request.POST.get('password')

    try:
        from django.contrib.auth.models import User
        user = User.objects.get(username=username)

        # Check if user exists and is active
        if not user.is_active:
            return JsonResponse({
                'error': 'User account is not active. Please verify your email first.',
                'user_exists': True,
                'is_active': False
            })

        # Try to authenticate
        auth_user = authenticate(username=username, password=password)
        if auth_user:
            return JsonResponse({'success': True, 'message': 'Authentication successful'})
        else:
            return JsonResponse({'error': 'Invalid password', 'user_exists': True, 'is_active': True})

    except User.DoesNotExist:
        return JsonResponse({'error': 'User does not exist', 'user_exists': False})
