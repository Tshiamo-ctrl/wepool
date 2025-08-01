# users/models.py - Update the Profile model to include new fields
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import uuid

class Profile(models.Model):
    MEMBER_TYPE_CHOICES = [
        ('paying', 'Paying Member'),
        ('sponsored', 'PIF Member'),  # Changed for display only
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('yellow', 'Yellow'),
        ('green', 'Green'),
        ('qualified', 'Qualified'),
    ]

    # Main user relationship
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, unique=True)
    referrer_phone = models.CharField(max_length=15, blank=True, null=True)
    member_type = models.CharField(max_length=10, choices=MEMBER_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    # Personal Information (removed address field)
    date_of_birth = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    # Verification and Links
    verified_email = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    registered_tacconnector = models.BooleanField(default=False)  # Changed field name
    tacconnector_link = models.URLField(blank=True, null=True)    # Changed field name

    # Payment tracking
    paid_for_self = models.BooleanField(default=False)
    paid_for_sponsored = models.BooleanField(default=False)

    # New fields for terms and communications
    agreed_to_terms = models.BooleanField(default=False)
    communications_opt_in = models.BooleanField(default=False)
    terms_agreed_date = models.DateTimeField(null=True, blank=True)

    # Qualification Override Fields
    qualification_overridden = models.BooleanField(
        default=False,
        help_text="Override normal qualification requirements"
    )
    override_reason = models.TextField(
        blank=True,
        help_text="Reason for overriding qualifications"
    )
    overridden_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qualification_overrides',
        help_text="Admin who overrode the qualification"
    )
    override_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the qualification was overridden"
    )

    # Admin Promotion Override Fields (Superuser only)
    admin_promotion_overridden = models.BooleanField(
        default=False,
        help_text="Override admin promotion requirements"
    )
    admin_override_reason = models.TextField(
        blank=True,
        help_text="Reason for admin promotion override"
    )
    admin_overridden_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_promotion_overrides',
        help_text="Superuser who overrode admin promotion"
    )
    admin_override_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When admin promotion was overridden"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.phone}"

    def get_member_type_display_ui(self):
        """Get display name for UI (PIF instead of sponsored)"""
        if self.member_type == 'sponsored':
            return 'PIF Member'
        return 'Paying Member'

# users/models.py - Update the qualification check methods
def check_yellow_qualification(self, override_check=False):
    """Check if user qualifies for Yellow status"""
    if self.qualification_overridden and not override_check:
        return False

    if (self.verified_email and
        self.registered_tacconnector and  # Updated field name
        self.tacconnector_link):          # Updated field name
        self.status = 'yellow'
        self.save()
        return True
    return False

    def check_sponsored_qualification(self, override_check=False):
        """Check if PIF member is qualified"""
        if self.qualification_overridden and not override_check:
            return False

        if self.member_type == 'sponsored':
            from core.models import Referral
            paying_referrals = Referral.objects.filter(
                referrer=self,
                referred__member_type='paying'
            ).count()
            if paying_referrals >= 4:
                self.status = 'qualified'
                self.save()
                return True
        return False

    def can_be_promoted_to_admin(self):
        """Check if user can be promoted to admin"""
        if self.admin_promotion_overridden:
            return True

        return (self.status == 'green' and
                self.paid_for_sponsored and
                self.paid_for_self)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()
