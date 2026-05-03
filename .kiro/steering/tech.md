# Technology Stack

## Backend

**Framework**: Django 6.0.3 (Python 3.13+)

**Key Dependencies**:
- `langchain` + `langchain-community` + `langchain-chroma` - RAG orchestration
- `langchain-huggingface` + `sentence-transformers` - Embedding models
- `psycopg2-binary` - PostgreSQL adapter
- `asgiref` - ASGI support

**Package Management**: `uv` (Python package manager)
- Lock file: `backend/uv.lock`
- Project config: `backend/pyproject.toml`

**Database**: PostgreSQL 17

**Vector Store**: ChromaDB (local persistence via mounted volume)

**LLM Runtime**: Ollama
- Default chat model: `qwen2.5:3b`
- Default embedding model: `nomic-embed-text-v2-moe`
- Base URL: `http://ollama:11434` (container networking)

## Frontend

**Framework**: React 19.2.4 with TypeScript 5.9.3

**Build Tool**: Vite 8.0.1

**Key Dependencies**:
- `react` + `react-dom` - UI framework
- `@vitejs/plugin-react` - Vite React plugin

**Dev Dependencies**:
- `eslint` + `typescript-eslint` - Linting
- `@types/react` + `@types/react-dom` - Type definitions

## Infrastructure

**Containerization**: Docker + Docker Compose
- Multi-service orchestration (backend, frontend, ollama, db)
- Volume mounts for development hot-reload
- GPU support for Ollama (requires Docker Desktop with GPU passthrough)

**Environment Configuration**: `.env` file at repository root
- Loaded by Django settings via custom `_load_env_file()` helper
- Container environments override via `docker-compose.yml`

## Common Commands

### Docker Operations

```bash
# Build and start all services
docker compose up -d --build

# Stop all services
docker compose down

# View logs
docker compose logs -f [service_name]

# Rebuild specific service
docker compose up -d --build backend
```

### Ollama Model Management

```bash
# Pull chat model
docker compose exec ollama ollama pull qwen2.5:3b

# Pull embedding model
docker compose exec ollama ollama pull nomic-embed-text-v2-moe

# List installed models
docker compose exec ollama ollama list
```

### Backend (Django)

```bash
# Run migrations (inside container)
docker compose exec backend python manage.py migrate

# Create superuser
docker compose exec backend python manage.py createsuperuser

# Run tests
docker compose exec backend python manage.py test

# Django shell
docker compose exec backend python manage.py shell
```

### Frontend (React)

```bash
# Install dependencies (inside container, auto-runs on startup)
docker compose exec frontend npm install

# Run linter
docker compose exec frontend npm run lint

# Build for production
docker compose exec frontend npm run build
```

## Development Notes

- **Container-first**: All development happens inside containers; host execution may fail due to service hostnames like `ollama` and `db`
- **Hot reload**: Both backend and frontend support live reload via volume mounts
- **Port mappings**:
  - Backend: `localhost:8000`
  - Frontend: `localhost:5173`
  - PostgreSQL: `localhost:5432`
  - Ollama: `localhost:11434`
- **Environment variables**: Keep `.env` aligned with Docker networking (use service names, not `localhost`)
