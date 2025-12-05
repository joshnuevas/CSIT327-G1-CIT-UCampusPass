from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils import timezone

class SimpleTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        # Works even if user has no last_login field
        return f"{user.pk}{user.email}{timestamp}"

simple_token_generator = SimpleTokenGenerator()
