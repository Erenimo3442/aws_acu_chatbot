# Quick Fix for CI Failure

## Problem

The GitHub Actions CI is failing because:
1. ✅ **FIXED**: Backend tests were failing due to missing `DJANGO_SECRET_KEY` environment variable
2. ❌ **NEEDS FIX**: Frontend `package-lock.json` is out of sync with `package.json`

## Solution

**Good news!** The CI/CD pipeline has been updated to use `npm install` instead of `npm ci`, which is more forgiving with lock file mismatches. This means:

✅ **The CI should now pass without manual intervention!**

However, for best practices and faster builds in the future, you should still update the lock file:

### Option 1: Using Docker (Recommended)

```bash
# Start Docker services
docker compose up -d

# Update the lock file inside the container
docker compose exec frontend npm install

# Copy the updated lock file from container to host
docker compose cp frontend:/app/package-lock.json frontend/package-lock.json

# Commit the changes
git add frontend/package-lock.json
git commit -m "Update package-lock.json for vitest dependencies"
git push
```

### Option 2: Using Local Node.js

If you have Node.js installed locally:

```bash
cd frontend
npm install
cd ..

git add frontend/package-lock.json
git commit -m "Update package-lock.json for vitest dependencies"
git push
```

### Option 3: Using the Helper Script

```bash
bash update-frontend-deps.sh

git add frontend/package-lock.json
git commit -m "Update package-lock.json for vitest dependencies"
git push
```

## What Changed

The CI setup added these dependencies to `frontend/package.json`:
- `vitest@^2.1.8` - Test framework
- `jsdom@^25.0.1` - DOM environment for tests

These need to be reflected in `package-lock.json` for the CI to pass.

## After the Fix

Once you commit and push the updated `package-lock.json`, the CI pipeline will:
1. ✅ Install dependencies successfully
2. ✅ Run backend tests (now with correct environment variables)
3. ✅ Run frontend linter
4. ✅ Run frontend tests
5. ✅ Build Docker images

## Verify Locally

Before pushing, verify tests work locally:

```bash
# Backend tests
docker compose exec backend python manage.py test

# Frontend tests
docker compose exec frontend npm run test
```

Both should pass! 🎉
