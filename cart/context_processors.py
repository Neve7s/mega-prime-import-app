from django.http import HttpRequest


def cart_count(request: HttpRequest) -> dict:
    # Stub: conteo real en Task 7. Devuelve 0 para no romper base.html.
    return {"cart_count": 0}
