#!/usr/bin/env python3
"""
Environment Configuration Validator for PantryPilot

This script validates that required environment variables are set
and provides helpful feedback for missing or insecure configurations.
"""

import sys
from pathlib import Path


def validate_env_file(env_file_path):
    """Validate environment file exists and contains required variables."""
    required_vars = [
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "SECRET_KEY",
        "CORS_ORIGINS",
        "ENVIRONMENT",
    ]

    warnings = []
    errors = []

    if not env_file_path.exists():
        errors.append(f"Environment file not found: {env_file_path}")
        return errors, warnings

    # Read environment file
    env_vars = {}
    with open(env_file_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value

    # Check required variables
    for var in required_vars:
        if var not in env_vars:
            errors.append(f"Missing required environment variable: {var}")
        elif not env_vars[var] or env_vars[var] == "CHANGE_ME_TO_STRONG_PASSWORD":
            errors.append(f"Environment variable {var} needs to be set to a real value")

    # Security checks
    if "POSTGRES_PASSWORD" in env_vars:
        password = env_vars["POSTGRES_PASSWORD"]
        if len(password) < 12:
            warnings.append("POSTGRES_PASSWORD should be at least 12 characters long")
        # Check for weak passwords, including a placeholder for development purposes
        if (
            password
            in ["password", "123456", "admin", "DEVELOPMENT_PASSWORD_PLACEHOLDER"]
            and env_vars.get("ENVIRONMENT") == "production"
        ):
            errors.append("POSTGRES_PASSWORD is too weak for production use")

    if "SECRET_KEY" in env_vars:
        secret = env_vars["SECRET_KEY"]
        if len(secret) < 32:
            warnings.append("SECRET_KEY should be at least 32 characters long")
        if "dev-secret-key" in secret and env_vars.get("ENVIRONMENT") == "production":
            errors.append(
                "SECRET_KEY appears to be a development key - change for production"
            )

    if "CORS_ORIGINS" in env_vars:
        origins = env_vars["CORS_ORIGINS"]
        if env_vars.get("ENVIRONMENT") == "production" and "localhost" in origins:
            warnings.append("CORS_ORIGINS contains localhost in production environment")

    return errors, warnings


def main():
    """Main validation function."""
    print("🔍 Validating PantryPilot Environment Configuration...\n")

    project_root = Path(__file__).parent.parent
    env_files = [
        (project_root / ".env.dev", "Development"),
        (project_root / ".env.prod", "Production"),
    ]

    total_errors = 0
    total_warnings = 0

    for env_file, env_name in env_files:
        print(f"📁 Checking {env_name} Environment ({env_file.name})")
        print("-" * 50)

        errors, warnings = validate_env_file(env_file)

        if errors:
            print("❌ ERRORS:")
            for error in errors:
                print(f"   • {error}")
            total_errors += len(errors)

        if warnings:
            print("⚠️  WARNINGS:")
            for warning in warnings:
                print(f"   • {warning}")
            total_warnings += len(warnings)

        if not errors and not warnings:
            print("✅ Configuration looks good!")

        print()

    # Summary
    print("📊 SUMMARY")
    print("-" * 20)
    print(f"Total Errors: {total_errors}")
    print(f"Total Warnings: {total_warnings}")

    if total_errors > 0:
        print("\n❌ Please fix the errors above before proceeding with Docker setup.")
        return 1
    elif total_warnings > 0:
        print("\n⚠️  Consider addressing the warnings above for better security.")
        return 0
    else:
        print("\n🎉 All environment files are properly configured!")
        return 0


if __name__ == "__main__":
    sys.exit(main())
