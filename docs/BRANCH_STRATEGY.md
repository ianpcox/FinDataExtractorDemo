# Branch Strategy - FinDataExtractor Vanilla

## Branch Overview

- **`main`** - Production-ready code, stable releases
- **`dev`** - Development branch, active development work

## Workflow

### Development Workflow

1. **Work on `dev` branch**
   ```bash
   git checkout dev
   git pull origin dev
   # Make your changes
   git add .
   git commit -m "Your changes"
   git push origin dev
   ```

2. **Merge to `main` when ready**
   - Create a pull request from `dev` to `main`
   - Review and test
   - Merge when stable

### Feature Development

For new features, create feature branches from `dev`:

```bash
git checkout dev
git pull origin dev
git checkout -b feature/your-feature-name
# Make changes
git push origin feature/your-feature-name
# Create PR to merge into dev
```

## Current Setup

- ✅ `main` branch - Initial release
- ✅ `dev` branch - Active development
- 🔄 Default branch: `main` (protected for production)

## Branch Protection (Recommended)

Consider setting up branch protection on GitHub:

1. Go to Settings > Branches
2. Add rule for `main` branch:
   - Require pull request reviews
   - Require status checks to pass
   - Require branches to be up to date
   - Do not allow force pushes

## Quick Reference

```bash
# Switch to dev branch
git checkout dev

# Create new feature branch
git checkout -b feature/new-feature

# Push new branch
git push -u origin feature/new-feature

# Update dev branch
git checkout dev
git pull origin dev
```

