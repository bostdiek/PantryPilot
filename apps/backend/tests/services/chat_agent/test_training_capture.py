"""Tests for training data capture service."""

import uuid

from models.users import User
from services.chat_agent.training_capture import _is_synthetic_user


class TestIsSyntheticUser:
    """Test synthetic user detection."""

    def test_synthetic_user_detected(self):
        """Should detect users with @pantrypilot.synthetic email"""
        user = User(
            id=uuid.uuid4(),
            username="synthetic-veggie-val",
            email="synthetic-veggie-val@pantrypilot.synthetic",
            hashed_password="fake",
            is_verified=True,
        )
        assert _is_synthetic_user(user) is True

    def test_real_user_not_synthetic(self):
        """Should not detect real users as synthetic"""
        user = User(
            id=uuid.uuid4(),
            username="realuser",
            email="realuser@gmail.com",
            hashed_password="fake",
            is_verified=True,
        )
        assert _is_synthetic_user(user) is False

    def test_synthetic_domain_case_insensitive(self):
        """Should match domains case-insensitively (RFC 5321)"""
        user = User(
            id=uuid.uuid4(),
            username="test",
            email="test@pantrypilot.SYNTHETIC",
            hashed_password="fake",
            is_verified=True,
        )
        # Email domains are case-insensitive per RFC 5321
        # so mixed-case synthetic domains should still be detected
        assert _is_synthetic_user(user) is True

    def test_similar_domain_not_synthetic(self):
        """Should not match similar but different domains"""
        user = User(
            id=uuid.uuid4(),
            username="test",
            email="test@pantrypilot.com",
            hashed_password="fake",
            is_verified=True,
        )
        assert _is_synthetic_user(user) is False

    def test_partial_match_not_synthetic(self):
        """Should not match partial domain"""
        user = User(
            id=uuid.uuid4(),
            username="test",
            email="test@synthetic",
            hashed_password="fake",
            is_verified=True,
        )
        assert _is_synthetic_user(user) is False

    def test_multiple_synthetic_users(self):
        """Should detect all persona users as synthetic"""
        persona_names = [
            "veggie-val",
            "family-fiona",
            "solo-sam",
            "gluten-free-grace",
            "adventurous-alex",
            "routine-rita",
            "fitness-frank",
            "dairy-free-dana",
        ]

        for name in persona_names:
            user = User(
                id=uuid.uuid4(),
                username=f"synthetic-{name}",
                email=f"synthetic-{name}@pantrypilot.synthetic",
                hashed_password="fake",
                is_verified=True,
            )
            assert _is_synthetic_user(user) is True, f"Failed for {name}"
