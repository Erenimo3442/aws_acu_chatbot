"""Admin dashboard views for monitoring the chatbot system."""

from datetime import timedelta

from django.http import HttpRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

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

        # Vector store stats
        vector_store_count = 0
        try:
            from rag.vector_store import init_vector_store_manager
            vsm, _ = init_vector_store_manager()
            collection = vsm.vectorstore._collection
            vector_store_count = collection.count()
        except Exception:
            pass

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
                    "vector_store_documents": vector_store_count,
                },
                "recent_sessions": recent_sessions,
            },
            status=200,
        )
    except ApiError as exc:
        return error_response(request, exc.status, exc.code, exc.message, exc.details, exc.retryable)


@csrf_exempt
@require_POST
def admin_run_scraper(request: HttpRequest):
    """POST /api/v1/admin/run-scraper — trigger the batch scraper."""
    try:
        context = resolve_auth_context(request)
        require_roles(context, {ROLE_ADMIN_STAFF})

        import json
        payload = json.loads(request.body.decode("utf-8") or "{}")
        max_programs = int(payload.get("max_programs", 0))

        from rag.scrape_runner import run_batch_scrape
        result = run_batch_scrape(
            dry_run=bool(payload.get("dry_run", False)),
            drupal_only=bool(payload.get("drupal_only", False)),
            bologna_only=bool(payload.get("bologna_only", False)),
            max_programs_per_level=max_programs,
        )

        return success_response(request, result, status=200)
    except ApiError as exc:
        return error_response(request, exc.status, exc.code, exc.message, exc.details, exc.retryable)
    except Exception as exc:
        return error_response(request, 500, "INTERNAL_ERROR", str(exc))
