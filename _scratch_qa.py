import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "megra_prime.settings")
django.setup()

from django.contrib.auth import get_user_model

U = get_user_model()
u, _ = U.objects.get_or_create(username="qa_v3_tmp", defaults={"is_staff": True})
u.is_staff = True
u.set_password("QaTmp!2026")
u.save()
print("ok", u.username, u.is_staff)
