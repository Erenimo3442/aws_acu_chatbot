# Product Overview

AWS ACU Chatbot is a university assistant chatbot that answers student and applicant questions using institution-specific content through retrieval-augmented generation (RAG).

## Core Capabilities

- **RAG-powered Q&A**: Uses Ollama LLM with vector store retrieval to answer questions with source citations
- **Session management**: Tracks conversation history across anonymous and authenticated users
- **Source attribution**: Provides citations with snippets, URLs, and page numbers for transparency
- **Feedback collection**: Captures user ratings (up/down) with optional reasons and comments
- **Content ingestion**: Admin/service endpoints for web-scraped university content processing

## User Roles

- **Anonymous**: Can chat and view their own sessions
- **Student**: Authenticated users with same chat permissions as anonymous
- **Admin/Staff**: Can ingest new content into the knowledge base
- **Internal Service**: Token-based access for automated ingestion pipelines

## Architecture

Container-first application with four services:
- Django backend API (Python)
- React frontend (TypeScript + Vite)
- Ollama for LLM inference and embeddings
- PostgreSQL for relational data and chat history
- ChromaDB for vector storage (mounted volume)

## API Contract

RESTful JSON API with standardized error envelopes:
- All responses include `ok`, `data`/`error`, and `meta` fields
- Request IDs for tracing
- Rate limiting with retry hints
- OpenAPI spec available at `backend/openapi.v1.yaml`
