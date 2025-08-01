# dashboard/forms.py
from django import forms
from django.contrib.auth.models import User
from users.models import Profile
from django.core.exceptions import ValidationError
from django.utils import timezone

class AdminUserEditForm(forms.ModelForm):
    """Form for editing User model fields with validation"""

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username (must be unique)'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'user@example.com'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Only superusers can modify is_staff
        if not (self.current_user and self.current_user.is_superuser):
            self.fields['is_staff'].disabled = True
            self.fields['is_staff'].help_text = 'Only superusers can modify admin status.'

        # Add help text
        self.fields['username'].help_text = 'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
        self.fields['email'].help_text = 'Enter a valid email address.'
        self.fields['is_active'].help_text = 'Designates whether this user should be treated as active.'
        self.fields['is_staff'].help_text = 'Designates whether the user can log into the admin site.'

    def clean_username(self):
        username = self.cleaned_data['username']
        existing_user = User.objects.filter(username=username).exclude(
            pk=self.instance.pk if self.instance else None
        ).first()

        if existing_user:
            raise ValidationError(f'Username "{username}" already exists. Please choose a different username.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        existing_user = User.objects.filter(email=email).exclude(
            pk=self.instance.pk if self.instance else None
        ).first()

        if existing_user:
            raise ValidationError(f'Email "{email}" is already in use by another user.')
        return email

class AdminProfileEditForm(forms.ModelForm):
    """Form for editing Profile model fields with override functionality"""

    class Meta:
        model = Profile
        fields = [
            'referrer_phone', 'member_type', 'status',
            'date_of_birth', 'city', 'state', 'country', 'zip_code',  # Removed 'address'
            'verified_email', 'registered_tacconnector', 'tacconnector_link',  # Updated field names
            'paid_for_self', 'paid_for_sponsored', 'communications_opt_in',
            'qualification_overridden', 'override_reason',
            'admin_promotion_overridden', 'admin_override_reason'
        ]
        widgets = {
            'referrer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'placeholder': 'Referrer phone (read-only reference)'
            }),
            'member_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City/Suburb'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State/Province'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'zip_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ZIP/Postal Code'
            }),
            'tacconnector_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://taconnector.africa/profile'
            }),
            'override_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain why normal qualification rules are being overridden...'
            }),
            'admin_override_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Explain why admin promotion rules are being overridden...'
            }),
        }
        labels = {
            'registered_tacconnector': 'Registered on TAC Connector',
            'tacconnector_link': 'TAC Connector Profile Link',
            'member_type': 'Membership Type',
            'communications_opt_in': 'Receives Communications',
        }

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Update choices for member_type to show UI-friendly labels
        self.fields['member_type'].choices = [
            ('paying', 'Paying Member'),
            ('sponsored', 'PIF Member')  # UI display change
        ]

        # Only show admin override fields to superusers
        if not (self.current_user and self.current_user.is_superuser):
            if 'admin_promotion_overridden' in self.fields:
                del self.fields['admin_promotion_overridden']
            if 'admin_override_reason' in self.fields:
                del self.fields['admin_override_reason']

        # Add help text
        self.fields['member_type'].help_text = 'Type of membership for this user.'
        self.fields['status'].help_text = 'Current qualification status.'
        self.fields['verified_email'].help_text = 'Has the user verified their email address?'
        self.fields['registered_tacconnector'].help_text = 'Is the user registered on TAC Connector?'
        self.fields['tacconnector_link'].help_text = 'User\'s TAC Connector profile URL.'
        self.fields['paid_for_self'].help_text = 'Has this user paid for themselves?'
        self.fields['paid_for_sponsored'].help_text = 'Has this user paid for a PIF member?'
        self.fields['communications_opt_in'].help_text = 'Does the user want to receive communications?'
        self.fields['qualification_overridden'].help_text = 'Check to bypass normal qualification requirements'
        self.fields['override_reason'].help_text = 'Required when overriding qualifications'

        if 'admin_promotion_overridden' in self.fields:
            self.fields['admin_promotion_overridden'].help_text = 'Allow promotion to admin regardless of qualification'
            self.fields['admin_override_reason'].help_text = 'Required when overriding admin promotion rules'

        # Make referrer_phone read-only
        self.fields['referrer_phone'].widget.attrs['readonly'] = True
        self.fields['referrer_phone'].help_text = 'Phone number of the user who referred this member (cannot be changed).'

    def clean(self):
        cleaned_data = super().clean()
        qualification_overridden = cleaned_data.get('qualification_overridden')
        override_reason = cleaned_data.get('override_reason')
        admin_promotion_overridden = cleaned_data.get('admin_promotion_overridden')
        admin_override_reason = cleaned_data.get('admin_override_reason')

        # Require reason when overriding qualifications
        if qualification_overridden and not override_reason:
            raise ValidationError({
                'override_reason': 'Reason is required when overriding qualifications.'
            })

        # Require reason when overriding admin promotion (superuser only)
        if admin_promotion_overridden and not admin_override_reason:
            raise ValidationError({
                'admin_override_reason': 'Reason is required when overriding admin promotion rules.'
            })

        return cleaned_data

class QualificationOverrideForm(forms.Form):
    """Standalone form for quick qualification overrides"""
    override_type = forms.ChoiceField(
        choices=[
            ('qualification', 'Override User Qualifications'),
            ('admin_promotion', 'Override Admin Promotion (Superuser Only)'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Explain the reason for this override...'
        }),
        help_text='Detailed explanation required for audit purposes'
    )
    confirm = forms.BooleanField(
        required=True,
        label='I confirm this override is necessary and justified',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop('current_user', None)
        super().__init__(*args, **kwargs)

        # Remove admin promotion option for non-superusers
        if not (self.current_user and self.current_user.is_superuser):
            self.fields['override_type'].choices = [
                ('qualification', 'Override User Qualifications')
            ]

class UserDeleteForm(forms.Form):
    """Confirmation form for user deletion"""
    confirm_deletion = forms.BooleanField(
        required=True,
        label="I confirm that I want to permanently delete this user",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    reason = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Optional: Reason for deletion',
            'class': 'form-control'
        }),
        label="Reason (optional)"
    )

class ProfileFilterForm(forms.Form):
    """Form for filtering profiles in the admin dashboard"""
    member_type = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('paying', 'Paying Members'),
            ('sponsored', 'PIF Members')  # UI display change
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Member Type'
    )
    status = forms.ChoiceField(
        choices=[('', 'All')] + Profile.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Status'
    )
    override_status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('overridden', 'Overridden Qualifications'),
            ('normal', 'Normal Qualifications'),
            ('admin_overridden', 'Admin Promotion Overridden'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Override Status'
    )
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by name, email, username, or phone',
            'class': 'form-control'
        }),
        label='Search'
    )

class BulkActionForm(forms.Form):
    """Form for bulk actions on multiple users"""
    ACTION_CHOICES = [
        ('', 'Select Action...'),
        ('update_status', 'Update Status'),
        ('toggle_active', 'Toggle Active Status'),
        ('toggle_communications', 'Toggle Communications'),
        ('export_selected', 'Export Selected Users'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Bulk Action'
    )

    new_status = forms.ChoiceField(
        choices=[('', 'Select Status...')] + Profile.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='New Status'
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        new_status = cleaned_data.get('new_status')

        if action == 'update_status' and not new_status:
            raise ValidationError({
                'new_status': 'Status is required when updating status.'
            })

        return cleaned_data

class TACConnectorUpdateForm(forms.Form):
    """Form for updating TAC Connector information"""
    registered_tacconnector = forms.BooleanField(
        required=False,
        label='Registered on TAC Connector',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    tacconnector_link = forms.URLField(
        required=False,
        label='TAC Connector Profile Link',
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://taconnector.africa/yourprofile'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        registered = cleaned_data.get('registered_tacconnector')
        link = cleaned_data.get('tacconnector_link')

        if registered and not link:
            raise ValidationError({
                'tacconnector_link': 'TAC Connector link is required when marked as registered.'
            })

        return cleaned_data

class AssignmentForm(forms.Form):
    """Form for assigning Yellow members to PIF members"""
    yellow_member = forms.ModelChoiceField(
        queryset=None,
        empty_label="Select Yellow Member...",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Yellow Member'
    )
    sponsored_member = forms.ModelChoiceField(
        queryset=None,
        empty_label="Select PIF Member...",
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='PIF Member'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set querysets for available members
        self.fields['yellow_member'].queryset = Profile.objects.filter(
            status='yellow',
            paid_for_sponsored=False
        ).select_related('user')

        self.fields['sponsored_member'].queryset = Profile.objects.filter(
            member_type='sponsored',
            status='qualified',
            paid_for_self=False
        ).select_related('user')

    def clean(self):
        cleaned_data = super().clean()
        yellow_member = cleaned_data.get('yellow_member')
        sponsored_member = cleaned_data.get('sponsored_member')

        if yellow_member and sponsored_member:
            if yellow_member == sponsored_member:
                raise ValidationError('Cannot assign a member to themselves.')

        return cleaned_data
