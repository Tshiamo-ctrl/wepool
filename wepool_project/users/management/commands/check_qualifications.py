# Management command for checking qualifications

from django.core.management.base import BaseCommand
from users.models import Profile

class Command(BaseCommand):
    help = 'Check and update qualifications for all users'

    def handle(self, *args, **options):
        # Check yellow qualifications
        pending_profiles = Profile.objects.filter(status='pending')
        yellow_qualified = 0

        for profile in pending_profiles:
            if profile.check_yellow_qualification():
                yellow_qualified += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Updated {yellow_qualified} profiles to Yellow status'
            )
        )

        # Check sponsored qualifications
        sponsored_profiles = Profile.objects.filter(
            member_type='sponsored',
            status__in=['pending', 'yellow']
        )
        sponsored_qualified = 0

        for profile in sponsored_profiles:
            if profile.check_sponsored_qualification():
                sponsored_qualified += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Updated {sponsored_qualified} sponsored members to Qualified status'
            )
        )
