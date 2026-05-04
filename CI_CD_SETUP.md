# CI/CD Setup Guide

This document explains the CI/CD setup for the AWS ACU Chatbot project.

## Overview

The project uses **GitHub Actions** for continuous integration. The pipeline automatically runs on every push and pull request to `main` and `develop` branches.

## What Gets Tested

### 1. Backend Tests (Django + Python)
- ✅ All Django unit tests in `backend/api_v1/tests/`
- ✅ PostgreSQL database integration
- ✅ Access control tests
- ✅ Rate limiting tests
- ✅ API contract tests
- ✅ Session ownership tests

### 2. Frontend Tests (React + TypeScript)
- ✅ ESLint code quality checks
- ✅ Vitest unit tests
- ✅ Production build verification

### 3. Docker Build Tests
- ✅ Backend Docker image builds successfully
- ✅ Frontend Docker image builds successfully

## Files Added

```
.github/
└── workflows/
    ├── ci.yml              # Main CI pipeline configuration
    └── README.md           # Detailed CI documentation

backend/
├── .env.test               # Test environment configuration
└── api_v1/tests/
    └── test_smoke.py       # Basic smoke tests

frontend/
├── vitest.config.ts        # Vitest test configuration
├── src/__tests__/
│   └── App.test.tsx        # Sample test file
└── package.json            # Updated with test dependencies

test.sh                     # Helper script to run all tests locally
update-frontend-deps.sh     # Helper script to update npm dependencies
CI_CD_SETUP.md             # This file
```

## Running Tests Locally

### Quick Start - Run All Tests

```bash
# Make sure Docker services are running
docker compose up -d

# Run all tests
bash test.sh
```

### Individual Test Commands

**Backend:**
```bash
docker compose exec backend python manage.py test
```

**Frontend:**
```bash
# First time: update dependencies
cd frontend && npm install && cd ..

# Run tests
docker compose exec frontend npm run test

# Run linter
docker compose exec frontend npm run lint
```

## GitHub Actions Workflow

The CI pipeline (`.github/workflows/ci.yml`) has three jobs:

### Job 1: backend-test
- Sets up Python 3.13 with `uv` package manager
- Starts PostgreSQL 17 service
- Installs backend dependencies
- Runs Django test suite

**Environment Variables:**
- `DJANGO_SECRET_KEY`: Test secret key
- `DATABASE_ENGINE`: postgresql
- `DATABASE_NAME`: chatbot_test
- `DATABASE_USERNAME`: postgres
- `DATABASE_PASSWORD`: postgres
- `DATABASE_HOST`: localhost
- `DATABASE_PORT`: 5432

### Job 2: frontend-test
- Sets up Node.js 20
- Installs npm dependencies
- Runs ESLint linter
- Runs Vitest tests
- Builds production bundle

### Job 3: docker-build
- Runs only if backend and frontend tests pass
- Builds Docker images for both services
- Uses GitHub Actions cache for faster builds
- Does not push images (just validates they build)

## Test Configuration

### Backend Test Configuration

The backend uses `.env.test` file for test-specific settings:
- Uses SQLite in-memory database for fast local tests
- CI overrides with PostgreSQL for integration testing
- Automatically loaded when running `python manage.py test`

### Frontend Test Configuration

The frontend uses Vitest with:
- `jsdom` environment for DOM testing
- Global test utilities
- React component testing support

## Troubleshooting

### Issue: "SECRET_KEY must not be empty"

**Solution:** The CI now correctly sets `DJANGO_SECRET_KEY` environment variable. If running locally, ensure `.env.test` exists in the backend directory.

### Issue: "npm ci" fails with lock file mismatch

**Solution:** We changed CI to use `npm install` instead of `npm ci`. To update the lock file locally:

```bash
cd frontend
npm install
git add package.json package-lock.json
git commit -m "Update frontend dependencies"
```

Or use the helper script:
```bash
bash update-frontend-deps.sh
```

### Issue: Docker not running

**Solution:** Start Docker services:
```bash
docker compose up -d
```

### Issue: Tests fail locally but pass in CI

**Possible causes:**
- Different database (SQLite locally vs PostgreSQL in CI)
- Missing environment variables
- Outdated dependencies

**Solution:** Run tests with the same configuration as CI:
```bash
# Backend with PostgreSQL
docker compose exec backend python manage.py test

# Frontend with all dependencies
docker compose exec frontend npm run test
```

## Adding New Tests

### Backend (Django)

Create test files in `backend/api_v1/tests/`:

```python
from django.test import TestCase

class MyFeatureTests(TestCase):
    def test_something(self):
        # Your test code
        self.assertEqual(1 + 1, 2)
```

### Frontend (React + Vitest)

Create test files in `frontend/src/__tests__/` or co-locate with components:

```typescript
import { describe, it, expect } from 'vitest';

describe('MyComponent', () => {
  it('should work correctly', () => {
    expect(true).toBe(true);
  });
});
```

## Next Steps

Consider adding:

- [ ] Code coverage reporting (Codecov, Coveralls)
- [ ] Deployment jobs for staging/production
- [ ] Integration tests with Docker Compose
- [ ] Security scanning (Dependabot, Snyk, Trivy)
- [ ] Performance testing
- [ ] E2E tests with Playwright or Cypress
- [ ] Automatic dependency updates
- [ ] Release automation

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Django Testing](https://docs.djangoproject.com/en/6.0/topics/testing/)
- [Vitest Documentation](https://vitest.dev/)
- [Docker Build Best Practices](https://docs.docker.com/build/building/best-practices/)
