from django.apps import AppConfig

class AccountsConfig(AppConfig):
    name = 'Account_Management'

    def ready(self):
        import Account_Management.signals  # ensures the signal gets registered
