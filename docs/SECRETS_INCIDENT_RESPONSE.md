# Secrets Exposure Incident Response Playbook

This document outlines the immediate steps to take when secrets (API keys, passwords, tokens, etc.) have been accidentally committed to version control or otherwise exposed.

## Immediate Response (Within 1 Hour)

### 1. Assess the Exposure
- **Determine what was exposed**: API keys, database passwords, tokens, certificates, etc.
- **Identify the scope**: Which systems, services, or accounts are affected?
- **Check exposure time**: When was the secret first committed? How long has it been exposed?
- **Verify public accessibility**: Is the repository public? Has it been forked or cloned?

### 2. Secure the Systems
- **Revoke compromised credentials immediately**:
  - Database passwords: Change in database and update application configs
  - API keys: Revoke in the respective service provider's console
  - JWT secrets: Generate new SECRET_KEY and invalidate existing sessions
  - SSH keys: Remove from authorized_keys and generate new ones
  - Cloud credentials: Disable access keys and create new ones

- **Monitor for unauthorized access**:
  - Check access logs for suspicious activity
  - Review recent login attempts and API usage
  - Monitor database connections and queries
  - Check cloud service usage patterns

### 3. Rotate All Affected Credentials
- **Generate new secrets** using cryptographically secure methods:
  ```bash
  # Generate new SECRET_KEY for JWT
  openssl rand -hex 32

  # Generate new database password
  openssl rand -base64 32
  ```

- **Update all deployment environments**:
  - Development environment variables
  - Staging environment configurations
  - Production environment secrets
  - CI/CD pipeline variables

## Git History Cleanup

### 4. Remove Secrets from Git History

⚠️ **Warning**: Rewriting git history can be disruptive. Coordinate with your team.

```bash
# Option 1: Use git-filter-repo (recommended)
pip install git-filter-repo
git filter-repo --invert-paths --path-glob '*.env' --path-glob '*.env.*'

# Option 2: Use BFG Repo Cleaner for large repos
# Download from: https://rtyley.github.io/bfg-repo-cleaner/
java -jar bfg.jar --delete-files .env
java -jar bfg.jar --replace-text passwords.txt  # File with SECRET=***REMOVED***

# Option 3: Manual removal with git filter-branch (last resort)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch .env .env.dev .env.prod' \
  --prune-empty --tag-name-filter cat -- --all
```

### 5. Force Push and Coordinate
```bash
# Force push to rewrite remote history (COORDINATE WITH TEAM)
git push origin --force --all
git push origin --force --tags

# Inform team members to re-clone or rebase their branches
```

## Communication and Documentation

### 6. Internal Communication
- **Notify development team** immediately about the exposure
- **Inform security team** or designated security contact
- **Alert operations team** about credential rotation
- **Document the incident** with timeline and affected systems

### 7. External Communication (if required)
- **Customer notification** if customer data might be at risk
- **Regulatory reporting** if required by compliance frameworks
- **Vendor notification** if third-party services are affected

## Prevention and Verification

### 8. Verify Remediation
- **Test new credentials** in all environments
- **Confirm old credentials are invalid**
- **Review access logs** for any unauthorized usage
- **Run security scans** to ensure no other secrets are exposed

### 9. Update Security Measures
- **Review and update** `.gitignore` to prevent future exposures
- **Enable secret scanning** in CI/CD pipeline (if not already enabled)
- **Add pre-commit hooks** for secret detection
- **Educate team members** on secure development practices

## Post-Incident Review

### 10. Conduct Post-Mortem
- **Document root cause** of the exposure
- **Identify process improvements** to prevent recurrence
- **Update training materials** and onboarding processes
- **Review and update** this playbook based on lessons learned

## Quick Reference Commands

### Emergency Credential Rotation
```bash
# Database password (safer: use interactive prompt)
psql -h localhost -U postgres
# Then, inside psql, run:
\password pantrypilot_user
# (You will be prompted securely for the new password)

# Generate new JWT secret
openssl rand -hex 32

# Update environment files
cp .env.example .env.dev
# Edit .env.dev with new credentials
```

### Secret Scanning
```bash
# Run secret scan
make secrets-scan

# Update baseline after fixing issues
make secrets-update

# Audit current state
make secrets-audit
```

### Git History Check
```bash
# Search for potential secrets in history
git log -p -S "password" --all
git log -p -S "secret" --all
git log -p -S "key" --all

# Check specific file history
git log -p -- .env .env.dev .env.prod
```

## Emergency Contacts

- **Development Team Lead**: [Contact Information]
- **Security Team**: [Contact Information]
- **Operations Team**: [Contact Information]
- **Incident Response**: [Contact Information]

## Additional Resources

- [OWASP Secrets Management Guide](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [Git Filter-Repo Documentation](https://github.com/newren/git-filter-repo)
- [BFG Repo Cleaner](https://rtyley.github.io/bfg-repo-cleaner/)

---

**Remember**: Speed is critical when secrets are exposed. The longer credentials remain valid after exposure, the higher the risk of compromise.
