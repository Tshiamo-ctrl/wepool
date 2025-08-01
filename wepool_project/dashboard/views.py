# dashboard/views.py - Complete import section
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User
from django.db import transaction
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from users.models import Profile
from core.models import Referral, Assignment
from .forms import (
    AdminUserEditForm,
    AdminProfileEditForm,
    ProfileFilterForm,
    UserDeleteForm,
    QualificationOverrideForm
)
import csv
import json
from datetime import datetime, timedelta

@staff_member_required
def admin_dashboard(request):
    """Main admin dashboard with statistics"""
    return render(request, 'dashboard/admin_dashboard.html')

@staff_member_required
def view_all_users(request):
    """View all users with filtering and override status"""
    form = ProfileFilterForm(request.GET)
    profiles = Profile.objects.select_related('user', 'overridden_by', 'admin_overridden_by').all()

    if form.is_valid():
        # Apply filters
        if form.cleaned_data['member_type']:
            profiles = profiles.filter(member_type=form.cleaned_data['member_type'])

        if form.cleaned_data['status']:
            profiles = profiles.filter(status=form.cleaned_data['status'])

        # Override status filter
        if form.cleaned_data.get('override_status'):
            override_status = form.cleaned_data['override_status']
            if override_status == 'overridden':
                profiles = profiles.filter(qualification_overridden=True)
            elif override_status == 'normal':
                profiles = profiles.filter(qualification_overridden=False)
            elif override_status == 'admin_overridden':
                profiles = profiles.filter(admin_promotion_overridden=True)

        if form.cleaned_data['search']:
            search_term = form.cleaned_data['search']
            profiles = profiles.filter(
                Q(user__first_name__icontains=search_term) |
                Q(user__last_name__icontains=search_term) |
                Q(user__email__icontains=search_term) |
                Q(user__username__icontains=search_term) |
                Q(phone__icontains=search_term)
            )

    return render(request, 'dashboard/view_all_users.html', {
        'profiles': profiles,
        'form': form
    })

@staff_member_required
def edit_user(request, profile_id):
    """Edit user with override functionality"""
    profile = get_object_or_404(Profile, id=profile_id)
    user = profile.user

    if request.method == 'POST':
        user_form = AdminUserEditForm(request.POST, instance=user, current_user=request.user)
        profile_form = AdminProfileEditForm(request.POST, instance=profile, current_user=request.user)

        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    # Save user information
                    updated_user = user_form.save()

                    # Handle profile save with override tracking
                    updated_profile = profile_form.save(commit=False)

                    # Track qualification override
                    if profile_form.cleaned_data.get('qualification_overridden') and not profile.qualification_overridden:
                        updated_profile.overridden_by = request.user
                        updated_profile.override_date = timezone.now()
                        messages.info(request, f'Qualification override applied by {request.user.username}')

                    # Track admin promotion override (superuser only)
                    if (request.user.is_superuser and
                        profile_form.cleaned_data.get('admin_promotion_overridden') and
                        not profile.admin_promotion_overridden):
                        updated_profile.admin_overridden_by = request.user
                        updated_profile.admin_override_date = timezone.now()

                        # If admin promotion is overridden, promote to staff
                        if updated_profile.admin_promotion_overridden:
                            updated_user.is_staff = True
                            updated_user.save()
                            messages.info(request, f'Admin promotion override applied - user promoted to staff')

                    # Save the profile
                    updated_profile.save()

                    # Check qualifications after update (unless overridden)
                    updated_profile.check_yellow_qualification()
                    updated_profile.check_sponsored_qualification()

                messages.success(
                    request,
                    f'All information for {updated_user.get_full_name()} has been updated successfully!'
                )
                return redirect('view_all_users')

            except Exception as e:
                messages.error(
                    request,
                    f'Error updating user: {str(e)}'
                )
        else:
            # Form validation failed
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = AdminUserEditForm(instance=user, current_user=request.user)
        profile_form = AdminProfileEditForm(instance=profile, current_user=request.user)

    # Get referral statistics
    from core.utils import get_referral_stats
    stats = get_referral_stats(profile)

    # Get referrals made by this user
    referrals_made = Referral.objects.filter(referrer=profile).select_related('referred__user')

    # Get who referred this user
    referrer = None
    if profile.referrer_phone:
        try:
            referrer = Profile.objects.get(phone=profile.referrer_phone)
        except Profile.DoesNotExist:
            pass

    # Get override history
    override_history = []
    if profile.qualification_overridden:
        override_history.append({
            'type': 'Qualification Override',
            'reason': profile.override_reason,
            'by': profile.overridden_by,
            'date': profile.override_date
        })

    if profile.admin_promotion_overridden:
        override_history.append({
            'type': 'Admin Promotion Override',
            'reason': profile.admin_override_reason,
            'by': profile.admin_overridden_by,
            'date': profile.admin_override_date
        })

    return render(request, 'dashboard/edit_user.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
        'user': user,
        'stats': stats,
        'referrals_made': referrals_made,
        'referrer': referrer,
        'override_history': override_history,
    })

@staff_member_required
def quick_override(request, profile_id):
    """Quick override form for qualifications"""
    profile = get_object_or_404(Profile, id=profile_id)

    if request.method == 'POST':
        form = QualificationOverrideForm(request.POST, current_user=request.user)

        if form.is_valid():
            override_type = form.cleaned_data['override_type']
            reason = form.cleaned_data['reason']

            try:
                with transaction.atomic():
                    if override_type == 'qualification':
                        profile.qualification_overridden = True
                        profile.override_reason = reason
                        profile.overridden_by = request.user
                        profile.override_date = timezone.now()
                        profile.save()

                        messages.success(request, f'Qualification override applied for {profile.user.get_full_name()}')

                    elif override_type == 'admin_promotion' and request.user.is_superuser:
                        profile.admin_promotion_overridden = True
                        profile.admin_override_reason = reason
                        profile.admin_overridden_by = request.user
                        profile.admin_override_date = timezone.now()

                        # Promote to staff
                        profile.user.is_staff = True
                        profile.user.save()
                        profile.save()

                        messages.success(request, f'Admin promotion override applied for {profile.user.get_full_name()}')

                    elif override_type == 'admin_promotion' and not request.user.is_superuser:
                        raise PermissionDenied("Only superusers can override admin promotion")

                return redirect('edit_user', profile_id=profile.id)

            except Exception as e:
                messages.error(request, f'Error applying override: {str(e)}')
    else:
        form = QualificationOverrideForm(current_user=request.user)

    return render(request, 'dashboard/quick_override.html', {
        'form': form,
        'profile': profile
    })

@staff_member_required
def remove_override(request, profile_id):
    """Remove override from a user"""
    profile = get_object_or_404(Profile, id=profile_id)

    if request.method == 'POST':
        override_type = request.POST.get('override_type')

        try:
            with transaction.atomic():
                if override_type == 'qualification':
                    profile.qualification_overridden = False
                    profile.override_reason = ''
                    profile.overridden_by = None
                    profile.override_date = None
                    profile.save()

                    # Re-check qualifications
                    profile.check_yellow_qualification()
                    profile.check_sponsored_qualification()

                    messages.success(request, f'Qualification override removed for {profile.user.get_full_name()}')

                elif override_type == 'admin_promotion':
                    if not request.user.is_superuser:
                        raise PermissionDenied("Only superusers can remove admin promotion overrides")

                    profile.admin_promotion_overridden = False
                    profile.admin_override_reason = ''
                    profile.admin_overridden_by = None
                    profile.admin_override_date = None

                    # Check if user should still be admin based on normal qualifications
                    if not profile.can_be_promoted_to_admin():
                        profile.user.is_staff = False
                        profile.user.save()
                        messages.info(request, f'Admin status removed - user no longer meets qualification requirements')

                    profile.save()
                    messages.success(request, f'Admin promotion override removed for {profile.user.get_full_name()}')

        except Exception as e:
            messages.error(request, f'Error removing override: {str(e)}')

    return redirect('edit_user', profile_id=profile.id)

@staff_member_required
def override_history(request):
    """View override history across all users"""
    # Get all profiles with overrides
    qualification_overrides = Profile.objects.filter(
        qualification_overridden=True
    ).select_related('user', 'overridden_by').order_by('-override_date')

    admin_overrides = Profile.objects.filter(
        admin_promotion_overridden=True
    ).select_related('user', 'admin_overridden_by').order_by('-admin_override_date')

    return render(request, 'dashboard/override_history.html', {
        'qualification_overrides': qualification_overrides,
        'admin_overrides': admin_overrides
    })

@staff_member_required
def delete_user(request, profile_id):
    """Delete user with override information in confirmation"""
    profile = get_object_or_404(Profile, id=profile_id)
    user = profile.user

    if request.method == 'POST':
        form = UserDeleteForm(request.POST)
        if form.is_valid():
            username = user.username
            email = user.email
            reason = form.cleaned_data.get('reason', '')

            # Log the deletion info including override information
            deletion_info = f"User '{username}' ({email}) deleted by {request.user.username}"
            if reason:
                deletion_info += f". Reason: {reason}"

            # Add override information to deletion log
            if profile.qualification_overridden:
                deletion_info += f". Had qualification override by {profile.overridden_by}"
            if profile.admin_promotion_overridden:
                deletion_info += f". Had admin promotion override by {profile.admin_overridden_by}"

            try:
                with transaction.atomic():
                    user.delete()

                messages.success(
                    request,
                    f'User {username} ({email}) has been permanently deleted.'
                )
                return redirect('view_all_users')

            except Exception as e:
                messages.error(
                    request,
                    f'Error deleting user: {str(e)}'
                )
    else:
        form = UserDeleteForm()

    # Get additional context for deletion confirmation
    from core.utils import get_referral_stats
    stats = get_referral_stats(profile)

    return render(request, 'dashboard/delete_user.html', {
        'form': form,
        'profile': profile,
        'user': user,
        'stats': stats
    })

# Keep existing views with minor updates for override information

@staff_member_required
def paying_queue(request):
    """Paying members queue with override status"""
    paying_profiles = Profile.objects.filter(
        member_type='paying',
        status='pending'
    ).select_related('user', 'overridden_by')

    return render(request, 'dashboard/paying_queue.html', {
        'profiles': paying_profiles
    })

@staff_member_required
def sponsored_queue(request):
    """Sponsored members queue with override status"""
    sponsored_profiles = Profile.objects.filter(
        member_type='sponsored',
        status='pending'
    ).select_related('user', 'overridden_by')

    return render(request, 'dashboard/sponsored_queue.html', {
        'profiles': sponsored_profiles
    })

@staff_member_required
def yellow_members(request):
    """Yellow members with override status"""
    yellow_profiles = Profile.objects.filter(
        status='yellow',
        paid_for_sponsored=False
    ).select_related('user', 'overridden_by')

    return render(request, 'dashboard/yellow_members.html', {
        'profiles': yellow_profiles
    })

@staff_member_required
def qualified_sponsored(request):
    """Qualified sponsored members with override status"""
    qualified_profiles = Profile.objects.filter(
        member_type='sponsored',
        status='qualified',
        paid_for_self=False
    ).select_related('user', 'overridden_by')

    return render(request, 'dashboard/qualified_sponsored.html', {
        'profiles': qualified_profiles
    })

@staff_member_required
def assign_members(request):
    """Assign yellow to sponsored members"""
    if request.method == 'POST':
        yellow_id = request.POST.get('yellow_member')
        sponsored_id = request.POST.get('sponsored_member')

        if yellow_id and sponsored_id:
            try:
                with transaction.atomic():
                    yellow = get_object_or_404(Profile, id=yellow_id)
                    sponsored = get_object_or_404(Profile, id=sponsored_id)

                    # Create assignment
                    assignment = Assignment.objects.create(
                        yellow_member=yellow,
                        sponsored_member=sponsored
                    )

                    # Update statuses
                    yellow.paid_for_sponsored = True
                    yellow.save()

                    sponsored.status = 'green'
                    sponsored.paid_for_self = True
                    sponsored.save()

                    assignment.completed = True
                    assignment.save()

                messages.success(
                    request,
                    f'Successfully assigned {yellow.user.get_full_name()} to sponsor {sponsored.user.get_full_name()}'
                )
            except Exception as e:
                messages.error(request, f'Error creating assignment: {str(e)}')

            return redirect('assign_members')

    # Get available members
    yellow_members = Profile.objects.filter(
        status='yellow',
        paid_for_sponsored=False
    ).select_related('user')

    sponsored_members = Profile.objects.filter(
        member_type='sponsored',
        status='qualified',
        paid_for_self=False
    ).select_related('user')

    # Get recent assignments
    assignments = Assignment.objects.filter(
        completed=True
    ).select_related('yellow_member__user', 'sponsored_member__user').order_by('-assigned_at')[:10]

    return render(request, 'dashboard/assign_members.html', {
        'yellow_members': yellow_members,
        'sponsored_members': sponsored_members,
        'assignments': assignments
    })

@staff_member_required
def export_data(request):
    """Export data with override information"""
    if request.method == 'POST':
        export_type = request.POST.get('export_type', 'csv')

        if export_type == 'csv':
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="wepool_users_with_overrides.csv"'

            writer = csv.writer(response)
            writer.writerow([
                'Username', 'Email', 'First Name', 'Last Name', 'Phone',
                'Member Type', 'Status', 'Referrer Phone', 'Verified Email',
                'Registered TechConnect', 'TechConnect Link', 'Is Active', 'Is Staff',
                'Qualification Overridden', 'Override Reason', 'Overridden By',
                'Admin Promotion Overridden', 'Admin Override Reason', 'Admin Override By',
                'Created At', 'Updated At'
            ])

            profiles = Profile.objects.select_related('user', 'overridden_by', 'admin_overridden_by').all()
            for profile in profiles:
                writer.writerow([
                    profile.user.username,
                    profile.user.email,
                    profile.user.first_name,
                    profile.user.last_name,
                    profile.phone,
                    profile.member_type,
                    profile.status,
                    profile.referrer_phone or '',
                    profile.verified_email,
                    profile.registered_techconnect,
                    profile.techconnect_link or '',
                    profile.user.is_active,
                    profile.user.is_staff,
                    profile.qualification_overridden,
                    profile.override_reason or '',
                    profile.overridden_by.username if profile.overridden_by else '',
                    profile.admin_promotion_overridden,
                    profile.admin_override_reason or '',
                    profile.admin_overridden_by.username if profile.admin_overridden_by else '',
                    profile.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    profile.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                ])

            return response

        elif export_type == 'sql':
            response = HttpResponse(content_type='text/plain')
            response['Content-Disposition'] = 'attachment; filename="wepool_users_with_overrides.sql"'

            sql_statements = []
            profiles = Profile.objects.select_related('user', 'overridden_by', 'admin_overridden_by').all()

            for profile in profiles:
                sql = f"""INSERT INTO profiles (username, email, first_name, last_name, phone, member_type, status, referrer_phone, verified_email, registered_techconnect, techconnect_link, is_active, is_staff, qualification_overridden, override_reason, overridden_by, admin_promotion_overridden, admin_override_reason, admin_override_by, created_at, updated_at) VALUES ('{profile.user.username}', '{profile.user.email}', '{profile.user.first_name}', '{profile.user.last_name}', '{profile.phone}', '{profile.member_type}', '{profile.status}', '{profile.referrer_phone or "NULL"}', {profile.verified_email}, {profile.registered_techconnect}, '{profile.techconnect_link or "NULL"}', {profile.user.is_active}, {profile.user.is_staff}, {profile.qualification_overridden}, '{profile.override_reason or "NULL"}', '{profile.overridden_by.username if profile.overridden_by else "NULL"}', {profile.admin_promotion_overridden}, '{profile.admin_override_reason or "NULL"}', '{profile.admin_overridden_by.username if profile.admin_overridden_by else "NULL"}', '{profile.created_at}', '{profile.updated_at}');"""
                sql_statements.append(sql)

            response.write('\n'.join(sql_statements))
            return response

    return render(request, 'dashboard/export_data.html')

@staff_member_required
def dashboard_stats(request):
    """API endpoint for dashboard statistics with override information"""
    from django.db.models import Count, Q

    # Get statistics
    total_users = Profile.objects.count()
    paying_members = Profile.objects.filter(member_type='paying').count()
    sponsored_members = Profile.objects.filter(member_type='sponsored').count()

    # Status counts
    pending_count = Profile.objects.filter(status='pending').count()
    yellow_count = Profile.objects.filter(status='yellow').count()
    green_count = Profile.objects.filter(status='green').count()
    qualified_count = Profile.objects.filter(status='qualified').count()

    # Override counts
    qualification_overrides = Profile.objects.filter(qualification_overridden=True).count()
    admin_overrides = Profile.objects.filter(admin_promotion_overridden=True).count()

    # Recent registrations (last 7 days)
    last_week = datetime.now() - timedelta(days=7)
    recent_registrations = Profile.objects.filter(
        created_at__gte=last_week
    ).count()

    # Assignment statistics
    total_assignments = Assignment.objects.filter(completed=True).count()
    pending_assignments = Assignment.objects.filter(completed=False).count()

    # Active users
    active_users = Profile.objects.filter(user__is_active=True).count()
    verified_emails = Profile.objects.filter(verified_email=True).count()

    data = {
        'total_users': total_users,
        'paying_members': paying_members,
        'sponsored_members': sponsored_members,
        'active_users': active_users,
        'verified_emails': verified_emails,
        'status_breakdown': {
            'pending': pending_count,
            'yellow': yellow_count,
            'green': green_count,
            'qualified': qualified_count
        },
        'overrides': {
            'qualification_overrides': qualification_overrides,
            'admin_overrides': admin_overrides
        },
        'recent_registrations': recent_registrations,
        'assignments': {
            'completed': total_assignments,
            'pending': pending_assignments
        }
    }

    return JsonResponse(data)

@staff_member_required
@require_http_methods(["POST"])
def bulk_update_status(request):
    """Bulk update user statuses and other bulk actions"""
    profile_ids = request.POST.getlist('profile_ids[]')
    action = request.POST.get('action')
    new_status = request.POST.get('new_status')

    if not profile_ids:
        return JsonResponse({'success': False, 'error': 'No users selected'})

    try:
        with transaction.atomic():
            if action == 'toggle_active':
                # Toggle active status for selected users
                updated_count = 0
                for profile_id in profile_ids:
                    try:
                        profile = Profile.objects.get(id=profile_id)
                        profile.user.is_active = not profile.user.is_active
                        profile.user.save()
                        updated_count += 1
                    except Profile.DoesNotExist:
                        pass

                return JsonResponse({
                    'success': True,
                    'updated_count': updated_count
                })

            elif new_status:
                # Update status for selected profiles
                updated_count = Profile.objects.filter(
                    id__in=profile_ids
                ).update(status=new_status)

                # Check qualifications for updated profiles (respect overrides)
                for profile_id in profile_ids:
                    try:
                        profile = Profile.objects.get(id=profile_id)
                        if not profile.qualification_overridden:
                            profile.check_yellow_qualification()
                            profile.check_sponsored_qualification()
                    except Profile.DoesNotExist:
                        pass

                return JsonResponse({
                    'success': True,
                    'updated_count': updated_count
                })

            else:
                return JsonResponse({'success': False, 'error': 'No valid action specified'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@staff_member_required
def process_yellow_queue(request):
    """Process yellow members to check their qualification"""
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        action = request.POST.get('action')

        if profile_id and action:
            try:
                profile = get_object_or_404(Profile, id=profile_id)

                if action == 'approve':
                    profile.status = 'yellow'
                    profile.save()
                    messages.success(request, f'{profile.user.get_full_name()} approved as Yellow member')
                elif action == 'reject':
                    profile.status = 'pending'
                    profile.save()
                    messages.warning(request, f'{profile.user.get_full_name()} status reverted to pending')

            except Exception as e:
                messages.error(request, f'Error processing request: {str(e)}')

            return redirect('yellow_members')

    return redirect('yellow_members')

# dashboard/views.py - Add these missing views

@staff_member_required
def override_history(request):
    """View override history across all users"""
    # Get all profiles with overrides
    qualification_overrides = Profile.objects.filter(
        qualification_overridden=True
    ).select_related('user', 'overridden_by').order_by('-override_date')

    admin_overrides = Profile.objects.filter(
        admin_promotion_overridden=True
    ).select_related('user', 'admin_overridden_by').order_by('-admin_override_date')

    return render(request, 'dashboard/override_history.html', {
        'qualification_overrides': qualification_overrides,
        'admin_overrides': admin_overrides
    })

@staff_member_required
def quick_override(request, profile_id):
    """Quick override form for qualifications"""
    profile = get_object_or_404(Profile, id=profile_id)

    if request.method == 'POST':
        form = QualificationOverrideForm(request.POST, current_user=request.user)

        if form.is_valid():
            override_type = form.cleaned_data['override_type']
            reason = form.cleaned_data['reason']

            try:
                with transaction.atomic():
                    if override_type == 'qualification':
                        profile.qualification_overridden = True
                        profile.override_reason = reason
                        profile.overridden_by = request.user
                        profile.override_date = timezone.now()
                        profile.save()

                        messages.success(request, f'Qualification override applied for {profile.user.get_full_name()}')

                    elif override_type == 'admin_promotion' and request.user.is_superuser:
                        profile.admin_promotion_overridden = True
                        profile.admin_override_reason = reason
                        profile.admin_overridden_by = request.user
                        profile.admin_override_date = timezone.now()

                        # Promote to staff
                        profile.user.is_staff = True
                        profile.user.save()
                        profile.save()

                        messages.success(request, f'Admin promotion override applied for {profile.user.get_full_name()}')

                    elif override_type == 'admin_promotion' and not request.user.is_superuser:
                        raise PermissionDenied("Only superusers can override admin promotion")

                return redirect('edit_user', profile_id=profile.id)

            except Exception as e:
                messages.error(request, f'Error applying override: {str(e)}')
    else:
        form = QualificationOverrideForm(current_user=request.user)

    return render(request, 'dashboard/quick_override.html', {
        'form': form,
        'profile': profile
    })

@staff_member_required
def remove_override(request, profile_id):
    """Remove override from a user"""
    profile = get_object_or_404(Profile, id=profile_id)

    if request.method == 'POST':
        override_type = request.POST.get('override_type')

        try:
            with transaction.atomic():
                if override_type == 'qualification':
                    profile.qualification_overridden = False
                    profile.override_reason = ''
                    profile.overridden_by = None
                    profile.override_date = None
                    profile.save()

                    # Re-check qualifications
                    profile.check_yellow_qualification()
                    profile.check_sponsored_qualification()

                    messages.success(request, f'Qualification override removed for {profile.user.get_full_name()}')

                elif override_type == 'admin_promotion':
                    if not request.user.is_superuser:
                        raise PermissionDenied("Only superusers can remove admin promotion overrides")

                    profile.admin_promotion_overridden = False
                    profile.admin_override_reason = ''
                    profile.admin_overridden_by = None
                    profile.admin_override_date = None

                    # Check if user should still be admin based on normal qualifications
                    if not profile.can_be_promoted_to_admin():
                        profile.user.is_staff = False
                        profile.user.save()
                        messages.info(request, f'Admin status removed - user no longer meets qualification requirements')

                    profile.save()
                    messages.success(request, f'Admin promotion override removed for {profile.user.get_full_name()}')

        except Exception as e:
            messages.error(request, f'Error removing override: {str(e)}')

    return redirect('edit_user', profile_id=profile.id)
