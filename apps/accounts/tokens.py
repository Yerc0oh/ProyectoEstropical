from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.crypto import constant_time_compare
from django.utils.http import base36_to_int


class ActivationTokenGenerator(PasswordResetTokenGenerator):
    """Token de verificación de correo. Incluye is_active, por lo que deja de
    ser válido una vez activada la cuenta (un solo uso)."""

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.is_active}{timestamp}"


class EmailChangeTokenGenerator(PasswordResetTokenGenerator):
    """Token para confirmar un cambio de correo electrónico.

    Vincula el token al usuario, al correo actual, al correo pendiente y a un
    nonce que se renueva con cada solicitud. Así, cambiar el correo actual,
    solicitar otro correo o confirmar el enlace invalida cualquier token previo.
    """

    key_salt = "apps.accounts.tokens.EmailChangeTokenGenerator"

    def _make_hash_value(self, user, timestamp):
        perfil = getattr(user, "perfil", None)
        correo_pendiente = getattr(perfil, "correo_pendiente", "") or ""
        nonce = getattr(perfil, "correo_pendiente_nonce", "") or ""
        return f"{user.pk}{user.email}{correo_pendiente}{nonce}{timestamp}"

    def check_token(self, user, token):
        """Igual que PasswordResetTokenGenerator pero con caducidad propia."""
        if not (user and token):
            return False
        try:
            ts_b36, _ = token.split("-")
        except ValueError:
            return False
        try:
            ts = base36_to_int(ts_b36)
        except ValueError:
            return False

        for secret in [self.secret, *self.secret_fallbacks]:
            if constant_time_compare(
                self._make_token_with_timestamp(user, ts, secret), token
            ):
                break
        else:
            return False

        timeout = getattr(settings, "EMAIL_CHANGE_TIMEOUT", settings.PASSWORD_RESET_TIMEOUT)
        return (self._num_seconds(self._now()) - ts) <= timeout


activation_token = ActivationTokenGenerator()
email_change_token = EmailChangeTokenGenerator()
