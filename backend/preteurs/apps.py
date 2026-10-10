from django.apps import AppConfig


class PreteursConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = 'preteurs'

    def reply(self):
        import preteurs.signals
