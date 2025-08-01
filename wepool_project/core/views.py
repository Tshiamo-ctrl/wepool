from django.shortcuts import render

# Create your views here.
# core/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from users.models import Profile
from .models import Referral
from .utils import build_referral_matrix, get_referral_stats

@login_required
def referral_matrix_view(request):
    """Display detailed referral matrix for current user"""
    profile = request.user.profile
    matrix = build_referral_matrix(profile)
    stats = get_referral_stats(profile)

    return render(request, 'core/referral_matrix.html', {
        'matrix': matrix,
        'stats': stats,
        'profile': profile
    })

@login_required
@require_http_methods(["GET"])
def get_referral_data(request):
    """API endpoint to get referral data for charts/visualizations"""
    profile = request.user.profile
    matrix = build_referral_matrix(profile)

    # Format data for response
    data = {
        'level_1': len(matrix['level_1']),
        'level_2': len(matrix['level_2']),
        'level_3': len(matrix['level_3']),
        'level_4': len(matrix['level_4']),
        'total': sum(len(matrix[level]) for level in matrix)
    }

    return JsonResponse(data)

@login_required
def direct_referrals_view(request):
    """View to show only direct referrals with detailed info"""
    profile = request.user.profile
    referrals = Referral.objects.filter(
        referrer=profile
    ).select_related('referred__user').order_by('-created_at')

    return render(request, 'core/direct_referrals.html', {
        'referrals': referrals,
        'profile': profile
    })
