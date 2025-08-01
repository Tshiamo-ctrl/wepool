# core/admin.py
from django.contrib import admin
from .models import Referral, Assignment

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ('referrer', 'referred', 'referrer_type', 'referred_type', 'created_at')
    list_filter = (
        'created_at',
        'referrer__member_type',
        'referred__member_type',
        'referrer__status',
        'referred__status'
    )
    search_fields = (
        'referrer__phone', 'referred__phone',
        'referrer__user__email', 'referred__user__email',
        'referrer__user__first_name', 'referrer__user__last_name',
        'referred__user__first_name', 'referred__user__last_name'
    )
    date_hierarchy = 'created_at'

    def referrer_type(self, obj):
        return obj.referrer.get_member_type_display_ui()
    referrer_type.short_description = 'Referrer Type'

    def referred_type(self, obj):
        return obj.referred.get_member_type_display_ui()
    referred_type.short_description = 'Referred Type'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'referrer__user', 'referred__user'
        )

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'yellow_member', 'sponsored_member', 'assigned_at', 'completed',
        'yellow_member_phone', 'sponsored_member_phone'
    )
    list_filter = ('completed', 'assigned_at')
    search_fields = (
        'yellow_member__phone', 'sponsored_member__phone',
        'yellow_member__user__first_name', 'yellow_member__user__last_name',
        'sponsored_member__user__first_name', 'sponsored_member__user__last_name'
    )
    date_hierarchy = 'assigned_at'

    def yellow_member_phone(self, obj):
        return obj.yellow_member.phone
    yellow_member_phone.short_description = 'Yellow Phone'

    def sponsored_member_phone(self, obj):
        return obj.sponsored_member.phone
    sponsored_member_phone.short_description = 'PIF Phone'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'yellow_member__user', 'sponsored_member__user'
        )
