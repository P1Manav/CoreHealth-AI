"""
Tests for the identity resolver — JWT verification and guest UUID handling.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import jwt
import time
from unittest.mock import patch
from flask import Flask

from app.identity.resolver import resolve_identity, require_identity


@pytest.fixture
def app():
    """Create a test Flask app."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    return app


class TestIdentityResolver:
    """Test the identity resolution logic."""

    def test_guest_uuid_valid(self, app):
        """Valid guest UUID should resolve to weak tier."""
        with app.test_request_context(
            headers={"X-Guest-Session-Id": "550e8400-e29b-41d4-a716-446655440000"}
        ):
            result = resolve_identity()
            assert result is None  # No error
            from flask import g
            assert g.identity["tier"] == "weak"
            assert g.identity["user_id"] == "550e8400-e29b-41d4-a716-446655440000"

    def test_guest_uuid_invalid_format(self, app):
        """Invalid UUID format should return 400."""
        with app.test_request_context(
            headers={"X-Guest-Session-Id": "not-a-valid-uuid"}
        ):
            result = resolve_identity()
            assert result is not None
            response, status = result
            assert status == 400

    def test_no_headers_returns_401(self, app):
        """No auth headers should return 401."""
        with app.test_request_context():
            result = resolve_identity()
            assert result is not None
            response, status = result
            assert status == 401

    @patch("app.identity.resolver.SUPABASE_JWT_SECRET", "test-secret-key-12345")
    def test_valid_jwt_strong_tier(self, app):
        """Valid JWT should resolve to strong tier."""
        token = jwt.encode(
            {
                "sub": "user-uuid-12345",
                "aud": "authenticated",
                "exp": int(time.time()) + 3600,
            },
            "test-secret-key-12345",
            algorithm="HS256",
        )
        with app.test_request_context(
            headers={"Authorization": f"Bearer {token}"}
        ):
            result = resolve_identity()
            assert result is None  # No error
            from flask import g
            assert g.identity["tier"] == "strong"
            assert g.identity["user_id"] == "user-uuid-12345"

    @patch("app.identity.resolver.SUPABASE_JWT_SECRET", "test-secret-key-12345")
    def test_expired_jwt_returns_401(self, app):
        """Expired JWT should return 401."""
        token = jwt.encode(
            {
                "sub": "user-uuid-12345",
                "aud": "authenticated",
                "exp": int(time.time()) - 3600,  # expired
            },
            "test-secret-key-12345",
            algorithm="HS256",
        )
        with app.test_request_context(
            headers={"Authorization": f"Bearer {token}"}
        ):
            result = resolve_identity()
            assert result is not None
            response, status = result
            assert status == 401

    def test_malformed_jwt_returns_401(self, app):
        """Malformed JWT should return 401."""
        with app.test_request_context(
            headers={"Authorization": "Bearer not.a.valid.jwt.token"}
        ):
            result = resolve_identity()
            assert result is not None
            response, status = result
            assert status == 401

    def test_bearer_prefix_required(self, app):
        """Authorization header without Bearer prefix should fall through to guest check."""
        with app.test_request_context(
            headers={"Authorization": "Basic somebase64"}
        ):
            result = resolve_identity()
            assert result is not None
            # Falls through to no-auth → 401
            response, status = result
            assert status == 401


class TestRequireIdentityDecorator:
    """Test the @require_identity decorator."""

    def test_decorator_blocks_without_auth(self, app):
        """Decorated endpoint should return 401 without auth."""
        @app.route("/test")
        @require_identity
        def test_route():
            return "ok"

        with app.test_client() as client:
            resp = client.get("/test")
            assert resp.status_code == 401

    def test_decorator_passes_with_guest_id(self, app):
        """Decorated endpoint should work with valid guest ID."""
        @app.route("/test")
        @require_identity
        def test_route():
            from flask import g
            return g.identity["tier"]

        with app.test_client() as client:
            resp = client.get(
                "/test",
                headers={"X-Guest-Session-Id": "550e8400-e29b-41d4-a716-446655440000"}
            )
            assert resp.status_code == 200
            assert resp.data.decode() == "weak"
