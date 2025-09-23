# Secret Scanning Developer Guide

This guide explains how to use the secret scanning tools implemented in PantryPilot to prevent accidentally committing sensitive information to version control.

## Overview

PantryPilot uses [detect-secrets](https://github.com/Yelp/detect-secrets) to scan for potential secrets in the codebase. The scanning happens both locally (via pre-commit hooks) and in CI pipelines.

## Local Development Setup

### 1. Install Pre-commit Hooks

```bash
# Install all dependencies (includes detect-secrets)
make install

# Install pre-commit hooks
cd apps/backend && uv run pre-commit install

# Or install manually if needed
pip install pre-commit
pre-commit install
```

### 2. Initial Secret Scan

Run a full scan to see current status:

```bash
# Run secret scanning
make secrets-scan

# View audit results and statistics
make secrets-audit
```

## Daily Usage

### Pre-commit Protection

Secret scanning runs automatically before each commit. If secrets are detected:

```bash
$ git commit -m "Add new feature"
detect-secrets-hook...............................................................Failed
- hook id: detect-secrets
- exit code: 1

ERROR: Potential secrets detected!
Review the findings in .secrets.baseline and resolve before committing.
```

### Manual Scanning

You can run scans manually at any time:

```bash
# Scan for new secrets
make secrets-scan

# Update baseline after resolving findings
make secrets-update

# View statistics and audit results
make secrets-audit
```

## Handling Secret Detections

### 1. Review Findings

When secrets are detected, examine the findings:

```bash
# View detailed audit
make secrets-audit

# Open the baseline file to see details
cat .secrets.baseline
```

### 2. Resolve True Positives

If real secrets are detected:

1. **Remove the secret** from the code
2. **Use environment variables** instead:
   ```python
   # Bad
   api_key = "sk-1234567890abcdef"

   # Good
   api_key = os.getenv("API_KEY")
   ```
3. **Update .env.example** with placeholder:
   ```bash
   API_KEY=your_api_key_here
   ```
4. **Update secrets baseline**:
   ```bash
   make secrets-update
   ```

### 3. Handle False Positives

For legitimate high-entropy strings that aren't secrets:

1. **Add inline comment** to allowlist:
   ```python
   # This is a test hash, not a real secret
   test_hash = "a1b2c3d4e5f6"  # pragma: allowlist secret
   ```

2. **Use specific patterns** to reduce false positives:
   ```python
   # Example: Use obvious test patterns
   test_token = "test_" + "fake_token_12345"
   ```

3. **Update baseline** if needed:
   ```bash
   make secrets-update
   ```

## CI Integration

### Automatic Scanning

Secret scanning runs in GitHub Actions for every:
- Push to main/develop branches
- Pull request

### CI Failure Handling

If CI fails due to secret detection:

1. **Review the CI logs** to see what was detected
2. **Fix the issue locally**:
   ```bash
   # Run scan to reproduce the issue
   make secrets-scan

   # Fix the detected secrets
   # Update baseline if needed
   make secrets-update

   # Commit and push the fix
   git add .secrets.baseline
   git commit -m "Update secrets baseline"
   git push
   ```

## Configuration

### Exclude Files/Patterns

Modify `.secrets.toml` to exclude files that don't need scanning:

```toml
exclude_files = [
    "^apps/frontend/node_modules/.*",
    "^apps/backend/.venv/.*",
    "^.git/.*",
    "^.*\\.log$",
    "^.*\\.coverage$"
]
```

### Plugin Configuration

Enable/disable specific secret detection plugins in `.secrets.toml`:

```toml
plugins_used = [
    { name = "AWSKeyDetector" },
    { name = "GitHubTokenDetector" },
    { name = "Base64HighEntropyString", limit = 4.5 },
    # Add or remove plugins as needed
]
```

## Best Practices

### 1. Environment Variables

Always use environment variables for sensitive data:

```python
# Backend (Python)
import os
from core.config import get_settings

settings = get_settings()
api_key = settings.API_KEY  # From environment

# Frontend (TypeScript)
const apiUrl = import.meta.env.VITE_API_URL;
```

### 2. Placeholder Values

Use obvious placeholders in example files:

```bash
# Good placeholders
SECRET_KEY=CHANGE_ME_TO_LONG_RANDOM_STRING
POSTGRES_PASSWORD=CHANGE_ME_TO_STRONG_PASSWORD
API_KEY=your_api_key_here

# Avoid realistic-looking fake values
SECRET_KEY=not-a-real-secret-key-123456789  # Could trigger detection
```

### 3. Test Data

For test data that might look like secrets:

```python
# Use obvious test prefixes
TEST_SECRET = "test_secret_not_real"
MOCK_API_KEY = "mock_key_12345"

# Or use pragma comments
real_looking_hash = "a1b2c3d4e5f6789"  # pragma: allowlist secret
```

### 4. Documentation

When documenting examples, use placeholders:

```markdown
# Bad
curl -H "Authorization: Bearer sk-1234567890abcdef" ...

# Good
curl -H "Authorization: Bearer YOUR_API_KEY" ...
```

## Troubleshooting

### Common Issues

1. **High entropy strings triggering false positives**:
   - Add `pragma: allowlist secret` comment
   - Use more obvious test/fake patterns
   - Adjust entropy thresholds in configuration

2. **Pre-commit hook failing**:
   ```bash
   # Update pre-commit hooks
   pre-commit autoupdate

   # Clear cache if needed
   pre-commit clean
   pre-commit install
   ```

3. **Baseline file conflicts**:
   ```bash
   # Regenerate baseline from scratch
   rm .secrets.baseline
   make secrets-scan > /dev/null 2>&1
   make secrets-audit
   ```

### Debug Commands

```bash
# Verbose secret scanning
cd apps/backend && uv run detect-secrets scan --all-files --verbose ../..

# Test specific file
cd apps/backend && uv run detect-secrets scan path/to/file.py

# Check plugin status
cd apps/backend && uv run detect-secrets scan --list-all-plugins
```

## Team Workflow

### Code Reviews

When reviewing code:
1. **Check for hardcoded secrets** in the diff
2. **Verify environment variables** are used properly
3. **Ensure .env files** are not committed

### Onboarding New Developers

1. **Run initial setup**:
   ```bash
   make install
   cd apps/backend && uv run pre-commit install
   ```

2. **Review security practices**:
   - Environment variable usage
   - Secret scanning workflow
   - Incident response playbook

3. **Test secret detection**:
   ```bash
   # Try to commit a fake secret to test the hook
   echo "api_key = 'sk-1234567890abcdef'" > test_secret.py
   git add test_secret.py
   git commit -m "Test secret detection"  # Should fail
   rm test_secret.py
   ```

## Additional Resources

- [detect-secrets Documentation](https://detect-secrets.readthedocs.io/)
- [Secrets Incident Response Playbook](./SECRETS_INCIDENT_RESPONSE.md)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)

## Quick Reference

```bash
# Daily commands
make secrets-scan          # Run secret detection
make secrets-audit         # View audit and statistics
make secrets-update        # Update baseline after fixes

# Setup commands
make install               # Install all dependencies
pre-commit install         # Install pre-commit hooks

# Troubleshooting
pre-commit run --all-files # Run all pre-commit hooks manually
pre-commit autoupdate      # Update hook versions
```
