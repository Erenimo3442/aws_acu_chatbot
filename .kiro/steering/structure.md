# Project Structure

## Repository Layout

```
aws_acu_chatbot/
├── backend/              # Django backend service
├── frontend/             # React frontend service
├── docs/                 # Project documentation
├── .env                  # Environment configuration (gitignored)
├── .env.example          # Environment template
├── docker-compose.yml    # Multi-service orchestration
└── README.md             # Project overview
```

## Backend Structure

```
backend/
├── api_v1/               # Main API application
│   ├── migrations/       # Database migrations
│   ├── tests/            # API test suite
│   ├── models.py         # Data models (ChatSession, ChatMessage, Citation, etc.)
│   ├── views.py          # API endpoints
│   ├── auth.py           # Authentication logic
│   ├── auth_views.py     # Auth endpoints
│   ├── admin.py          # Admin models
│   ├── admin_views.py    # Admin endpoints
│   ├── rate_limit.py     # Rate limiting utilities
│   ├── responses.py      # Response envelope helpers
│   ├── errors.py         # Error handling
│   └── urls.py           # URL routing
├── chatbot/              # Django project configuration
│   ├── settings.py       # Django settings (env loading, DB config, rate limits)
│   ├── urls.py           # Root URL configuration
│   ├── wsgi.py           # WSGI entry point
│   └── asgi.py           # ASGI entry point
├── rag/                  # RAG implementation
│   ├── agent.py          # LangChain agent with search tool
│   ├── vector_store.py   # ChromaDB vector store setup
│   ├── web_scrape_processor.py  # Content ingestion
│   └── api_views.py      # RAG-specific endpoints
├── chromadb-data/        # Vector store persistence (mounted volume)
├── logs/                 # Application logs
├── manage.py             # Django management script
├── pyproject.toml        # Python dependencies (uv)
├── uv.lock               # Dependency lock file
├── Dockerfile            # Backend container definition
├── openapi.v1.yaml       # OpenAPI specification
├── README.md             # Backend API documentation
└── README_API_CONTRACT_V1.md  # Detailed API contract
```

## Frontend Structure

```
frontend/
├── src/
│   ├── components/       # React components
│   │   ├── ConversationPanel.tsx  # Main chat interface
│   │   ├── SessionSidebar.tsx     # Session history sidebar
│   │   ├── SourcePanel.tsx        # Citation details panel
│   │   ├── MessageCitations.tsx   # Citation display
│   │   ├── MessageFeedback.tsx    # Feedback UI
│   │   ├── Masthead.tsx           # Header component
│   │   ├── LoginPage.tsx          # Authentication page
│   │   └── StatusBar.tsx          # Status indicator
│   ├── services/         # API service layer
│   │   ├── chatService.ts    # Chat operations
│   │   └── authService.ts    # Authentication operations
│   ├── lib/              # Shared utilities
│   │   └── apiClient.ts      # HTTP client with error handling
│   ├── hooks/            # React hooks
│   │   └── useChat.ts        # Chat state management
│   ├── models/           # Domain models
│   │   └── chat.ts           # Chat message types
│   ├── types/            # TypeScript types
│   │   └── api.ts            # API response types
│   ├── utils/            # Helper functions
│   │   └── dateTime.ts       # Date formatting
│   ├── assets/           # Static assets (images, icons)
│   ├── App.tsx           # Root component
│   ├── App.css           # Global styles
│   ├── main.tsx          # Application entry point
│   └── index.css         # Base styles
├── public/               # Static public assets
├── node_modules/         # Dependencies (gitignored)
├── package.json          # NPM dependencies and scripts
├── package-lock.json     # Dependency lock file
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript configuration
├── tsconfig.app.json     # App-specific TS config
├── tsconfig.node.json    # Node-specific TS config
├── eslint.config.js      # ESLint configuration
└── README.md             # Frontend documentation
```

## Key Conventions

### Backend (Django)

- **App structure**: Single `api_v1` app contains all API endpoints
- **Model naming**: Use prefixed IDs (`ses_`, `msg_`, `fb_`, `job_ing_`) via `prefixed_id()` helper
- **URL patterns**: All API routes under `/api/v1/` prefix
- **Response format**: Standardized envelope with `ok`, `data`/`error`, `meta` fields (see `responses.py`)
- **Error handling**: Centralized error codes and HTTP status mapping (see `errors.py`)
- **Rate limiting**: Per-endpoint configuration via Django settings
- **Authentication**: Session-based for students, token-based for internal services
- **Tests**: Located in `api_v1/tests/`, organized by feature

### Frontend (React + TypeScript)

- **Component organization**: Functional components with TypeScript
- **State management**: React hooks (useState, useEffect) + custom hooks
- **API layer**: Centralized in `lib/apiClient.ts` with typed responses
- **Service layer**: Domain-specific services wrap API client (e.g., `chatService.ts`)
- **Type definitions**: API types in `types/api.ts`, domain models in `models/`
- **Styling**: Component-specific CSS files co-located with components
- **Error handling**: `HttpError` class with structured error details

### RAG Implementation

- **Agent pattern**: LangChain agent with single `search_academic_documents` tool
- **Retriever**: ChromaDB vector store with configurable similarity search
- **Source tracking**: Global state in `agent.py` captures latest sources for citation
- **Embedding**: Ollama embedding model via LangChain integration
- **Chunking**: Handled in `web_scrape_processor.py` during ingestion

### Docker Volumes

- `postgres_data`: PostgreSQL database persistence
- `ollama_data`: Ollama model storage
- `frontend_node_modules`: Frontend dependencies (performance optimization)
- `./backend:/app`: Backend code hot-reload
- `./backend/chromadb-data:/app/chromadb-data`: Vector store persistence

## Configuration Files

- `.env`: Environment variables (database credentials, API keys, model IDs, rate limits)
- `docker-compose.yml`: Service definitions, networking, volume mounts
- `backend/chatbot/settings.py`: Django configuration with env loading
- `frontend/vite.config.ts`: Vite build configuration
- `backend/openapi.v1.yaml`: API contract specification
