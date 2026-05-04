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
# First, update package-lock.json if you modified package.json
cd frontend
npm install

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

## Important: Keeping package-lock.json in Sync

When you add new dependencies to `frontend/package.json`:

1. Run `npm install` in the frontend directory to update `package-lock.json`
2. Commit both `package.json` and `package-lock.json` together
3. The CI pipeline uses `npm install` to handle dependency installation

**Note:** The CI currently uses `npm install` instead of `npm ci` to be more forgiving with lock file updates during development. For production deployments, consider switching back to `npm ci` for stricter dependency management.

## Environment Variables for CI

The CI pipeline uses these environment variables (matching Django settings expectations):

- `DJANGO_SECRET_KEY`: Django secret key for session signing
- `DEBUG`: Set to "0" for tests
- `DATABASE_ENGINE`: Database backend (postgresql for CI, sqlite3 for local)
- `DATABASE_NAME`: Database name
- `DATABASE_USERNAME`: Database user
- `DATABASE_PASSWORD`: Database password
- `DATABASE_HOST`: Database host
- `DATABASE_PORT`: Database port
- `OLLAMA_BASE_URL`: Ollama service URL (not used in tests)
- `OLLAMA_CHAT_MODEL`: Chat model identifier
- `OLLAMA_EMBEDDING_MODEL`: Embedding model identifier

## Test Environment Configuration

The backend includes a `.env.test` file that is automatically loaded when running tests. This file:
- Uses SQLite in-memory database for fast local tests
- Sets appropriate test values for all required settings
- Can be overridden by environment variables in CI

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
