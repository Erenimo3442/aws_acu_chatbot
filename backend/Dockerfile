FROM python:3.13-slim

# Install `uv`
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create the app directory
RUN mkdir /app
 
# Set the working directory
WORKDIR /app
 
# Set environment variables to optimize Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONUNBUFFERED=1 
 
COPY pyproject.toml ./
RUN uv pip install --system --no-cache -r pyproject.toml
 
RUN useradd -m -r appuser && \
   chown -R appuser /app
 
# Copy application code
COPY --chown=appuser:appuser . .
 
# Switch to non-root user
USER appuser
 
# Expose the application port
EXPOSE 8000 
 
# Start the application using Gunicorn
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
