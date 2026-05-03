FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Optimize Python and uv for container environments
ENV PYTHONUNBUFFERED=1 
ENV UV_SYSTEM_PYTHON=1
# Force bytecode compilation during the build for faster app startup
ENV UV_COMPILE_BYTECODE=1 

# Copy ONLY dependency files first to maximize Docker layer caching
COPY pyproject.toml uv.lock* ./

# Use BuildKit cache mounts to drastically speed up dependency installation on rebuilds
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system -r pyproject.toml

# Create a non-root user and set permissions early
RUN useradd -m -r appuser && \
    chown -R appuser /app

# Copy application code securely
COPY --chown=appuser:appuser . .

# Switch to the non-root user for execution
USER appuser

EXPOSE 8000
 
# Start the application using Gunicorn
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
