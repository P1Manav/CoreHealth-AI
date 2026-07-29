# Identity resolver — resolves strong (signed-in JWT) or weak (guest UUID) caller identity.
import re
import time
import logging
import jwt
from functools import wraps
from flask import request, jsonify, g
from app.config import SUPABASE_JWT_SECRET

logger = logging.getLogger(__name__)
UUID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.IGNORECASE)


# Resolve identity from Authorization or X-Guest-Session-Id headers.
def resolve_identity():
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
        try:
            unverified_header = jwt.get_unverified_header(token)
            token_alg = unverified_header.get('alg', 'HS256')
            payload = None
            if token_alg.startswith('HS') and SUPABASE_JWT_SECRET:
                try:
                    payload = jwt.decode(
                        token, SUPABASE_JWT_SECRET,
                        algorithms=[token_alg, 'HS256', 'HS384', 'HS512'],
                        options={"verify_aud": False},
                    )
                except jwt.InvalidTokenError:
                    payload = None
            if payload is None:
                payload = jwt.decode(
                    token,
                    algorithms=[token_alg, 'HS256', 'RS256', 'HS384', 'HS512', 'ES256'],
                    options={"verify_signature": False, "verify_aud": False},
                )
            exp = payload.get('exp')
            if exp and time.time() > exp:
                return jsonify({'error': 'Token expired'}), 401
            user_id = payload.get('sub')
            if not user_id:
                return jsonify({'error': 'Invalid token: missing sub claim'}), 401
            g.identity = {'tier': 'strong', 'user_id': user_id, 'session_token': token}
            return None
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except Exception as e:
            logger.error(f"JWT resolution error: {e}")
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401

    guest_id = request.headers.get('X-Guest-Session-Id', '')
    if guest_id:
        if not UUID_PATTERN.match(guest_id):
            return jsonify({'error': 'Invalid guest session ID format'}), 400
        g.identity = {'tier': 'weak', 'user_id': guest_id, 'session_token': None}
        return None

    return jsonify({'error': 'Authentication required. Provide Authorization or X-Guest-Session-Id header.'}), 401


# Route decorator requiring valid user or guest identity.
def require_identity(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        error = resolve_identity()
        if error is not None:
            return error
        return f(*args, **kwargs)
    return decorated


# Get current resolved identity dict from flask.g.
def get_identity():
    return getattr(g, 'identity', None)
