# CI/CD Pipeline Visual Guide

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    CODE PUSH TO GITHUB                       │
│                  (main or develop branch)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   GITHUB ACTIONS TRIGGERED                   │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
┌───────────────────────────┐   ┌───────────────────────────┐
│    JOB 1: backend-test    │   │   JOB 2: frontend-test    │
│                           │   │                           │
│  ┌─────────────────────┐ │   │  ┌─────────────────────┐  │
│  │ Setup PostgreSQL 17 │ │   │  │ Setup Node.js 20    │  │
│  └─────────────────────┘ │   │  └─────────────────────┘  │
│            ↓              │   │            ↓              │
│  ┌─────────────────────┐ │   │  ┌─────────────────────┐  │
│  │ Install Python 3.13 │ │   │  │ npm install         │  │
│  └─────────────────────┘ │   │  └─────────────────────┘  │
│            ↓              │   │            ↓              │
│  ┌─────────────────────┐ │   │  ┌─────────────────────┐  │
│  │ Install uv          │ │   │  │ npm run lint        │  │
│  └─────────────────────┘ │   │  └─────────────────────┘  │
│            ↓              │   │            ↓              │
│  ┌─────────────────────┐ │   │  ┌─────────────────────┐  │
│  │ uv sync             │ │   │  │ npm run test        │  │
│  └─────────────────────┘ │   │  └─────────────────────┘  │
│            ↓              │   │            ↓              │
│  ┌─────────────────────┐ │   │  ┌─────────────────────┐  │
│  │ python manage.py    │ │   │  │ npm run build       │  │
│  │ test                │ │   │  └─────────────────────┘  │
│  └─────────────────────┘ │   │                           │
│            ↓              │   │            ↓              │
│       ✅ PASS             │   │       ✅ PASS             │
└───────────────────────────┘   └───────────────────────────┘
                │                           │
                └─────────────┬─────────────┘
                              ▼
                ┌─────────────────────────┐
                │  JOB 3: docker-build    │
                │                         │
                │  ┌───────────────────┐  │
                │  │ Setup Docker      │  │
                │  │ Buildx            │  │
                │  └───────────────────┘  │
                │           ↓             │
                │  ┌───────────────────┐  │
                │  │ Build backend     │  │
                │  │ Docker image      │  │
                │  └───────────────────┘  │
                │           ↓             │
                │  ┌───────────────────┐  │
                │  │ Build frontend    │  │
                │  │ Docker image      │  │
                │  └───────────────────┘  │
                │           ↓             │
                │      ✅ PASS            │
                └─────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────┐
                │   ALL CHECKS PASSED ✅   │
                │   Ready to merge/deploy │
                └─────────────────────────┘
```

## Job Details

### Job 1: Backend Test (8-10 seconds)

```
┌──────────────────────────────────────┐
│ PostgreSQL Service                   │
│ • Image: postgres:17                 │
│ • Database: chatbot_test             │
│ • Health checks enabled              │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ Test Environment                     │
│ • Python: 3.13                       │
│ • Package Manager: uv                │
│ • Database: PostgreSQL               │
│ • SECRET_KEY: test-secret-key        │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ Test Execution                       │
│ • 33 Django tests                    │
│ • Access control                     │
│ • Rate limiting                      │
│ • API contracts                      │
│ • Session ownership                  │
└──────────────────────────────────────┘
```

### Job 2: Frontend Test (30-40 seconds)

```
┌──────────────────────────────────────┐
│ Node.js Environment                  │
│ • Version: 20                        │
│ • Package Manager: npm               │
│ • Cache: Enabled                     │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ Quality Checks                       │
│ • ESLint: Code quality               │
│ • TypeScript: Type checking          │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ Test Execution                       │
│ • Vitest: Unit tests                 │
│ • jsdom: DOM environment             │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ Build Verification                   │
│ • TypeScript compilation             │
│ • Vite production build              │
│ • Asset optimization                 │
└──────────────────────────────────────┘
```

### Job 3: Docker Build (2-3 minutes)

```
┌──────────────────────────────────────┐
│ Backend Image Build                  │
│ • Base: python:3.13-slim             │
│ • Dependencies: uv sync              │
│ • User: appuser (non-root)           │
│ • Cache: GitHub Actions cache        │
└──────────────────────────────────────┘
              ↓
┌──────────────────────────────────────┐
│ Frontend Image Build                 │
│ • Stage 1: node:20-alpine (build)    │
│ • Stage 2: nginx:alpine (serve)      │
│ • Output: /usr/share/nginx/html      │
│ • Cache: GitHub Actions cache        │
└──────────────────────────────────────┘
```

## Trigger Conditions

```
┌─────────────────────────────────────────┐
│ Pipeline runs on:                       │
│                                         │
│ ✅ Push to main branch                  │
│ ✅ Push to develop branch               │
│ ✅ Pull request to main                 │
│ ✅ Pull request to develop              │
│                                         │
│ ❌ Does NOT run on:                     │
│    • Feature branches                   │
│    • Tags                               │
│    • Draft PRs (runs on ready)          │
└─────────────────────────────────────────┘
```

## Success Criteria

```
┌─────────────────────────────────────────┐
│ ✅ All backend tests pass (33/33)       │
│ ✅ No linting errors                    │
│ ✅ All frontend tests pass              │
│ ✅ Production build succeeds            │
│ ✅ Backend Docker image builds          │
│ ✅ Frontend Docker image builds         │
└─────────────────────────────────────────┘
```

## Failure Scenarios

```
┌─────────────────────────────────────────┐
│ ❌ Backend test fails                   │
│    → Fix test or code                   │
│    → Push again                         │
│                                         │
│ ❌ Linting errors                       │
│    → Run: npm run lint                  │
│    → Fix errors                         │
│    → Push again                         │
│                                         │
│ ❌ Docker build fails                   │
│    → Check Dockerfile                   │
│    → Test locally: docker build .       │
│    → Push again                         │
└─────────────────────────────────────────┘
```

## Cache Strategy

```
┌─────────────────────────────────────────┐
│ GitHub Actions Cache                    │
│                                         │
│ • npm dependencies (frontend)           │
│ • Docker layers (backend & frontend)    │
│ • Python packages (uv cache)            │
│                                         │
│ Benefits:                               │
│ • Faster builds (2-3x speedup)          │
│ • Reduced bandwidth                     │
│ • Lower costs                           │
└─────────────────────────────────────────┘
```

## Monitoring

```
┌─────────────────────────────────────────┐
│ View Results:                           │
│                                         │
│ 1. Go to GitHub repository              │
│ 2. Click "Actions" tab                  │
│ 3. See all workflow runs                │
│ 4. Click on a run for details           │
│ 5. View logs for each job               │
└─────────────────────────────────────────┘
```

## Typical Run Times

| Job | Duration | Notes |
|-----|----------|-------|
| backend-test | ~10s | With cache |
| frontend-test | ~40s | With cache |
| docker-build | ~3m | First run: ~5m |
| **Total** | **~4m** | **Parallel execution** |

---

**Note:** Times are approximate and depend on GitHub Actions runner availability and cache hits.
