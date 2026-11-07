from django.contrib.auth.tokens import PasswordResetTokenGenerator


class ActivationTokenGenerator(PasswordResetTokenGenerator):
    """Token de verificación de correo. Incluye is_active, por lo que deja de
    ser válido una vez activada la cuenta (un solo uso)."""

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.is_active}{timestamp}"


activation_token = ActivationTokenGenerator()
