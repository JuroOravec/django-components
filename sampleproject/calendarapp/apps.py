from django.apps import AppConfig


class CalendarappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "calendarapp"

    # TODO DELETE
    def ready(self) -> None:
        from django_vue.apps import main

        main()
