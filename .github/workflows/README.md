# CI/CD Pipeline

This directory contains GitHub Actions workflows for continuous integration and deployment.

## Workflows

### CI Pipeline (`ci.yml`)

Runs on every push and pull request to `main` and `develop` branches.

**Jobs:**

1. **backend-test**
   - Sets up PostgreSQL test database
   - Installs Python 3.13 and dependencies via `uv`
   - Runs Django test suite
   - Tests include: access control, rate limiting, session ownership, response contracts

2. **frontend-test**
   - Sets up Node.js 20
   - Installs npm dependencies
   - Runs ESLint for code quality
   - Runs Vitest unit tests
   - Builds production bundle to verify no build errors

3. **docker-build**
   - Runs after backend and frontend tests pass
   - Builds Docker images for both services
   - Uses GitHub Actions cache for faster builds
   - Verifies Docker images can be built successfully

## Running Tests Locally

### Backend Tests

```bash
# Inside Docker container
docker compose exec backend python manage.py test

# Or locally with uv
cd backend
uv run python manage.py test
```

### Frontend Tests

```bash
# Inside Docker container
docker compose exec frontend npm run test

# Or locally
cd frontend
npm run test

# Watch mode for development
npm run test:watch
```

### Linting

```bash
# Frontend linting
cd frontend
npm run lint
```

## Environment Variables for CI

The CI pipeline uses these environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Django secret key (test value)
- `DEBUG`: Set to "False" for tests
- `OLLAMA_BASE_URL`: Ollama service URL (not used in tests)
- `OLLAMA_CHAT_MODEL`: Chat model identifier
- `OLLAMA_EMBEDDING_MODEL`: Embedding model identifier

## Adding New Tests

### Backend (Django)

Add test files to `backend/api_v1/tests/`:

```python
from django.test import TestCase

class MyTestCase(TestCase):
    def test_something(self):
        self.assertEqual(1 + 1, 2)
```

### Frontend (React + Vitest)

Add test files to `frontend/src/__tests__/` or co-locate with components:

```typescript
import { describe, it, expect } from 'vitest';

describe('MyComponent', () => {
  it('should work', () => {
    expect(true).toBe(true);
  });
});
```

## Future Enhancements

- Add code coverage reporting
- Add deployment jobs for staging/production
- Add integration tests with Docker Compose
- Add security scanning (Dependabot, Snyk)
- Add performance testing
- Add E2E tests with Playwright/Cypress
