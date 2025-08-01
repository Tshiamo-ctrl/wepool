# core/utils.py
from .models import Referral

def build_referral_matrix(profile):
    """Build a 4-level referral matrix for a profile"""
    matrix = {
        'level_1': [],
        'level_2': [],
        'level_3': [],
        'level_4': []
    }

    # Level 1 - Direct referrals
    level_1_referrals = Referral.objects.filter(referrer=profile).select_related('referred__user')
    matrix['level_1'] = [ref.referred for ref in level_1_referrals]

    if matrix['level_1']:
        # Level 2
        level_2_referrals = Referral.objects.filter(
            referrer__in=matrix['level_1']
        ).select_related('referred__user')
        matrix['level_2'] = [ref.referred for ref in level_2_referrals]

        if matrix['level_2']:
            # Level 3
            level_3_referrals = Referral.objects.filter(
                referrer__in=matrix['level_2']
            ).select_related('referred__user')
            matrix['level_3'] = [ref.referred for ref in level_3_referrals]

            if matrix['level_3']:
                # Level 4
                level_4_referrals = Referral.objects.filter(
                    referrer__in=matrix['level_3']
                ).select_related('referred__user')
                matrix['level_4'] = [ref.referred for ref in level_4_referrals]

    return matrix

def get_referral_stats(profile):
    """Get referral statistics for a profile"""
    stats = {
        'total_referrals': 0,
        'paying_referrals': 0,
        'sponsored_referrals': 0,
        'active_referrals': 0
    }

    referrals = Referral.objects.filter(referrer=profile).select_related('referred')
    stats['total_referrals'] = referrals.count()

    for referral in referrals:
        if referral.referred.member_type == 'paying':
            stats['paying_referrals'] += 1
        else:
            stats['sponsored_referrals'] += 1

        if referral.referred.status in ['yellow', 'green']:
            stats['active_referrals'] += 1

    return stats
