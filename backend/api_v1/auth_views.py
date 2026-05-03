"""Session-based authentication views for the v1 API."""

import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .auth import ROLE_ANONYMOUS, resolve_auth_context
from .errors import ApiError
from .responses import error_response, success_response


@csrf_exempt
@require_POST
def login_view(request: HttpRequest):
    """POST /api/v1/auth/login — session-cookie based login.

    Request body: {"username": "...", "password": "..."}
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return error_response(request, 400, "VALIDATION_ERROR", "Invalid JSON payload.")

    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()

    if not username or not password:
        details = []
        if not username:
            details.append({"field": "username", "reason": "required"})
        if not password:
            details.append({"field": "password", "reason": "required"})
        return error_response(
            request, 400, "VALIDATION_ERROR", "Invalid request payload.",
            details=details,
        )

    user = authenticate(request, username=username, password=password)
    if user is None:
        return error_response(request, 401, "UNAUTHORIZED", "Invalid username or password.")

    login(request, user)

    return success_response(
        request,
        {
            "user": {
                "id": user.id,
                "username": user.username,
                "is_staff": user.is_staff,
                "role": "admin/staff" if user.is_staff or user.is_superuser else "student",
            }
        },
        status=200,
    )


@csrf_exempt
@require_POST
def register_view(request: HttpRequest):
    """POST /api/v1/auth/register — create a new student account.

    Request body: {"username": "...", "password": "...", "email": "..."}
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return error_response(request, 400, "VALIDATION_ERROR", "Invalid JSON payload.")

    username = (payload.get("username") or "").strip()
    password = (payload.get("password") or "").strip()
    email = (payload.get("email") or "").strip()

    details = []
    if not username or len(username) < 3:
        details.append({"field": "username", "reason": "too_short"})
    if not password or len(password) < 6:
        details.append({"field": "password", "reason": "too_short"})
    if details:
        return error_response(request, 400, "VALIDATION_ERROR", "Invalid request payload.", details=details)

    User = get_user_model()
    if User.objects.filter(username=username).exists():
        return error_response(request, 409, "CONFLICT", "Username already taken.")

    user = User.objects.create_user(username=username, password=password, email=email)
    login(request, user)

    return success_response(
        request,
        {
            "user": {
                "id": user.id,
                "username": user.username,
                "role": "student",
            }
        },
        status=201,
    )


@csrf_exempt
@require_POST
def logout_view(request: HttpRequest):
    """POST /api/v1/auth/logout — clear the session cookie."""
    logout(request)
    return success_response(request, {"message": "Logged out."}, status=200)


@csrf_exempt
@require_POST
def whoami_view(request: HttpRequest):
    """POST /api/v1/auth/whoami — return current user info or anonymous."""
    context = resolve_auth_context(request)

    if context.role == ROLE_ANONYMOUS:
        return success_response(request, {"authenticated": False, "role": "anonymous"}, status=200)

    return success_response(
        request,
        {
            "authenticated": True,
            "role": context.role,
            "user": {
                "id": context.user.id,
                "username": context.user.username,
                "is_staff": context.user.is_staff if context.user else False,
            } if context.user else None,
        },
        status=200,
    )
