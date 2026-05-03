from django.urls import path

from . import admin_views
from . import auth_views
from . import views


urlpatterns = [
    path("chat", views.chat, name="chat"),
    path("sessions", views.session_list, name="session-list"),
    path("sessions/create", views.session_create, name="session-create"),
    path("sessions/<str:id>/messages", views.session_messages, name="session-messages"),
    path("feedback", views.feedback, name="feedback"),
    path("sources/<str:source_id>", views.source_by_id, name="source-by-id"),
    path("ingest", views.ingest, name="ingest"),
    path("auth/login", auth_views.login_view, name="auth-login"),
    path("auth/register", auth_views.register_view, name="auth-register"),
    path("auth/logout", auth_views.logout_view, name="auth-logout"),
    path("auth/whoami", auth_views.whoami_view, name="auth-whoami"),
    path("admin/dashboard", admin_views.admin_dashboard, name="admin-dashboard"),
]
