# users/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Profile

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    # Specify which foreign key to use for the inline relationship
    fk_name = 'user'

    # Organize fields into sections
    fieldsets = (
        ('Basic Information', {
            'fields': ('phone', 'referrer_phone', 'member_type', 'status')
        }),
        ('Personal Details', {
            'fields': ('date_of_birth', 'city', 'state', 'country', 'zip_code'),  # Removed 'address'
            'classes': ('collapse',)
        }),
        ('Verification & Links', {
            'fields': ('verified_email', 'registered_tacconnector', 'tacconnector_link')  # Updated field names
        }),
        ('Payment Status', {
            'fields': ('paid_for_self', 'paid_for_sponsored')
        }),
        ('Terms & Communications', {
            'fields': ('agreed_to_terms', 'terms_agreed_date', 'communications_opt_in'),
            'classes': ('collapse',)
        }),
        ('Override Information', {
            'fields': (
                'qualification_overridden', 'override_reason', 'overridden_by', 'override_date',
                'admin_promotion_overridden', 'admin_override_reason', 'admin_overridden_by', 'admin_override_date'
            ),
            'classes': ('collapse',)
        }),
    )

    # Make override tracking fields read-only
    readonly_fields = (
        'terms_agreed_date', 'overridden_by', 'override_date',
        'admin_overridden_by', 'admin_override_date'
    )

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'is_staff',
        'get_member_type', 'get_status', 'get_verified_email'
    )

    def get_member_type(self, obj):
        if hasattr(obj, 'profile'):
            return obj.profile.get_member_type_display_ui()  # Use UI display method
        return 'N/A'
    get_member_type.short_description = 'Member Type'

    def get_status(self, obj):
        return obj.profile.status if hasattr(obj, 'profile') else 'N/A'
    get_status.short_description = 'Status'

    def get_verified_email(self, obj):
        if hasattr(obj, 'profile'):
            return '✓' if obj.profile.verified_email else '✗'
        return 'N/A'
    get_verified_email.short_description = 'Email Verified'

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'phone', 'member_type_display', 'status', 'verified_email',
        'registered_tacconnector', 'qualification_overridden', 'admin_promotion_overridden', 'created_at'  # Updated field name
    )
    list_filter = (
        'member_type', 'status', 'verified_email', 'registered_tacconnector',  # Updated field name
        'qualification_overridden', 'admin_promotion_overridden', 'communications_opt_in', 'agreed_to_terms'
    )
    search_fields = (
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'phone', 'referrer_phone'
    )
    date_hierarchy = 'created_at'

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'phone', 'referrer_phone', 'member_type', 'status')
        }),
        ('Personal Information', {
            'fields': ('date_of_birth', 'city', 'state', 'country', 'zip_code'),  # Removed 'address'
            'classes': ('collapse',)
        }),
        ('Verification & Links', {
            'fields': (
                'verified_email', 'email_verification_token',
                'registered_tacconnector', 'tacconnector_link'  # Updated field names
            )
        }),
        ('Terms & Communications', {
            'fields': ('agreed_to_terms', 'terms_agreed_date', 'communications_opt_in'),
            'classes': ('collapse',)
        }),
        ('Payment Tracking', {
            'fields': ('paid_for_self', 'paid_for_sponsored')
        }),
        ('Qualification Override', {
            'fields': (
                'qualification_overridden', 'override_reason',
                'overridden_by', 'override_date'
            ),
            'description': 'Override normal qualification requirements'
        }),
        ('Admin Promotion Override', {
            'fields': (
                'admin_promotion_overridden', 'admin_override_reason',
                'admin_overridden_by', 'admin_override_date'
            ),
            'description': 'Override admin promotion requirements (Superuser only)'
        }),
    )

    # Make tracking fields read-only
    readonly_fields = (
        'email_verification_token', 'terms_agreed_date', 'overridden_by', 'override_date',
        'admin_overridden_by', 'admin_override_date'
    )

    def member_type_display(self, obj):
        """Display member type with UI-friendly labels"""
        return obj.get_member_type_display_ui()
    member_type_display.short_description = 'Member Type'

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(self.readonly_fields)

        # Only superusers can modify admin promotion override
        if not request.user.is_superuser:
            readonly_fields.extend([
                'admin_promotion_overridden', 'admin_override_reason'
            ])

        return readonly_fields

    def save_model(self, request, obj, form, change):
        # Track who made the override
        if change:  # Only for existing objects
            try:
                original = Profile.objects.get(pk=obj.pk)

                # Track qualification override
                if obj.qualification_overridden and not original.qualification_overridden:
                    obj.overridden_by = request.user
                    obj.override_date = timezone.now()

                # Track admin promotion override (superuser only)
                if (request.user.is_superuser and
                    obj.admin_promotion_overridden and
                    not original.admin_promotion_overridden):
                    obj.admin_overridden_by = request.user
                    obj.admin_override_date = timezone.now()
            except Profile.DoesNotExist:
                pass

        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        """Optimize queries by selecting related objects"""
        return super().get_queryset(request).select_related(
            'user', 'overridden_by', 'admin_overridden_by'
        )
