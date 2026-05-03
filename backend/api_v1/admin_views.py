"""Admin dashboard views for monitoring the chatbot system."""

from datetime import timedelta

from django.http import HttpRequest
from django.utils import timezone
from django.views.decorators.http import require_GET

from .auth import ROLE_ADMIN_STAFF, require_roles, resolve_auth_context
from .errors import ApiError
from .models import ChatMessage, ChatSession, Citation, Feedback, IngestJob, SourceChunk
from .responses import error_response, success_response


@require_GET
def admin_dashboard(request: HttpRequest):
    """GET /api/v1/admin/dashboard — summary stats for admin panel."""
    try:
        context = resolve_auth_context(request)
        require_roles(context, {ROLE_ADMIN_STAFF})

        now = timezone.now()
        last_24h = now - timedelta(hours=24)

        total_sessions = ChatSession.objects.count()
        sessions_24h = ChatSession.objects.filter(created_at__gte=last_24h).count()
        total_messages = ChatMessage.objects.count()
        total_citations = Citation.objects.count()
        total_feedback = Feedback.objects.count()

        feedback_up = Feedback.objects.filter(rating=Feedback.RATING_UP).count()
        feedback_down = Feedback.objects.filter(rating=Feedback.RATING_DOWN).count()

        total_ingest_jobs = IngestJob.objects.count()
        total_source_chunks = SourceChunk.objects.count()

        recent_sessions = list(
            ChatSession.objects.order_by("-created_at")[:10].values(
                "id", "owner_type", "status", "created_at"
            )
        )

        return success_response(
            request,
            {
                "stats": {
                    "total_sessions": total_sessions,
                    "sessions_last_24h": sessions_24h,
                    "total_messages": total_messages,
                    "total_citations": total_citations,
                    "total_feedback": total_feedback,
                    "feedback_up": feedback_up,
                    "feedback_down": feedback_down,
                    "total_ingest_jobs": total_ingest_jobs,
                    "total_source_chunks": total_source_chunks,
                },
                "recent_sessions": recent_sessions,
            },
            status=200,
        )
    except ApiError as exc:
        return error_response(request, exc.status, exc.code, exc.message, exc.details, exc.retryable)
