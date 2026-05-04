# CI/CD Quick Reference

## 🚀 One Command to Rule Them All

```bash
bash test.sh
```

This runs all tests locally in Docker containers.

## 📋 Individual Commands

### Backend Tests
```bash
docker compose exec backend python manage.py test
```

### Frontend Tests
```bash
docker compose exec frontend npm run test
```

### Frontend Linting
```bash
docker compose exec frontend npm run lint
```

### Build Frontend for Production
```bash
docker compose exec frontend npm run build
```

## 🔧 Fix CI Failure

The CI is currently failing because `package-lock.json` needs to be updated:

```bash
cd frontend
npm install
git add package-lock.json
git commit -m "Update package-lock.json for test dependencies"
git push
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | CI pipeline configuration |
| `backend/.env.test` | Test environment variables |
| `backend/api_v1/tests/test_smoke.py` | Basic smoke tests |
| `frontend/Dockerfile` | Production Docker build |
| `frontend/vitest.config.ts` | Test configuration |
| `test.sh` | Run all tests locally |

## 🎯 CI Pipeline Jobs

1. **backend-test** → Runs Django tests with PostgreSQL
2. **frontend-test** → Runs linting, tests, and build
3. **docker-build** → Builds Docker images for both services

## ✅ Success Checklist

- [x] Backend tests passing (33/33)
- [x] Backend Dockerfile exists
- [x] Frontend Dockerfile created
- [x] Frontend tests configured
- [ ] Frontend `package-lock.json` updated ← **YOU ARE HERE**
- [ ] All CI jobs passing on GitHub

## 🐛 Common Issues

### "SECRET_KEY must not be empty"
✅ **Fixed** - CI now sets `DJANGO_SECRET_KEY` correctly

### "npm ci fails with lock file mismatch"
⚠️ **Action Required** - Run `npm install` in frontend directory

### "No Dockerfile in frontend"
✅ **Fixed** - Created `frontend/Dockerfile` for production builds

### RAG service warnings during tests
ℹ️ **Non-critical** - Tests use fallback answers and pass successfully

## 📚 Documentation

- `CI_CD_SETUP.md` - Complete setup guide
- `CI_STATUS.md` - Current status and known issues
- `QUICK_FIX.md` - Step-by-step fix for current CI issue
- `.github/workflows/README.md` - CI workflow details

## 🔗 Useful Links

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Django Testing](https://docs.djangoproject.com/en/6.0/topics/testing/)
- [Vitest Docs](https://vitest.dev/)
- [Docker Build Docs](https://docs.docker.com/build/)

---

**Need help?** Check `CI_CD_SETUP.md` for detailed documentation.
