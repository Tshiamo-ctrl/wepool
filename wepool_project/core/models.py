#from django.db import models

# Create your models here.
from django.db import models
from users.models import Profile

class Referral(models.Model):
    referrer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='referrals_made')
    referred = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='referral_received')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['referrer', 'referred']

    def __str__(self):
        return f"{self.referrer} referred {self.referred}"

class Assignment(models.Model):
    """Track Yellow-Sponsored assignments"""
    yellow_member = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='yellow_assignments')
    sponsored_member = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='sponsored_assignments')
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Yellow: {self.yellow_member} -> Sponsored: {self.sponsored_member}"
