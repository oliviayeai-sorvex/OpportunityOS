from __future__ import annotations

import json
import os
import bcrypt
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib import request, error
from uuid import uuid4


@dataclass
class AuthContext:
    user_id: str
    email: str
    role: str
    access_token: str


class AuthService:
    """Auth bridge: Supabase Auth when configured, local dev auth fallback otherwise."""

    def __init__(self) -> None:
        self._supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
        self._supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
        self._use_supabase = bool(self._supabase_url and self._supabase_anon_key)
        self._local_auth_path = Path(__file__).resolve().parents[1] / "data" / "local_auth_users.json"

        default_users: dict[str, dict] = {
            "dev-viewer-token": {"user_id": "user-viewer", "email": "viewer@local.dev", "role": "viewer", "password": "viewer1234"},
            "dev-operator-token": {"user_id": "user-operator", "email": "operator@local.dev", "role": "operator", "password": "operator1234"},
            "dev-admin-token": {"user_id": "user-admin", "email": "admin@local.dev", "role": "admin", "password": "admin1234"},
        }
        self._local_users: dict[str, dict] = self._load_local_users(default_users)

    def is_supabase_enabled(self) -> bool:
        return self._use_supabase

    def _load_local_users(self, default_users: dict[str, dict]) -> dict[str, dict]:
        if self._use_supabase:
            return default_users
        try:
            self._local_auth_path.parent.mkdir(parents=True, exist_ok=True)
            if self._local_auth_path.exists():
                raw = json.loads(self._local_auth_path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    merged = dict(default_users)
                    for token, user in raw.items():
                        if isinstance(token, str) and isinstance(user, dict):
                            # Default users have plain text passwords; local saved users have hashed passwords.
                            # We don't hash default_users here because they are static defaults.
                            merged[token] = user
                    return merged
        except (OSError, ValueError, TypeError):
            pass
        return default_users

    def _save_local_users(self) -> None:
        if self._use_supabase:
            return
        try:
            self._local_auth_path.parent.mkdir(parents=True, exist_ok=True)
            self._local_auth_path.write_text(json.dumps(self._local_users), encoding="utf-8")
        except OSError:
            pass

    def _http_json(self, method: str, url: str, headers: dict, payload: dict | None = None) -> dict:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = request.Request(url=url, method=method, data=data, headers=headers)
        with request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def sign_up(self, email: str, password: str) -> dict:
        if self._use_supabase:
            return self._http_json(
                "POST",
                f"{self._supabase_url}/auth/v1/signup",
                {
                    "apikey": self._supabase_anon_key,
                    "Content-Type": "application/json",
                },
                {"email": email, "password": password},
            )

        token = f"local-{uuid4()}"
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        self._local_users[token] = {"user_id": f"user-{uuid4()}", "email": email, "role": "operator", "password_hash": hashed}
        self._save_local_users()
        return {"access_token": token, "user": {"email": email}}

    def login(self, email: str, password: str) -> dict:
        if self._use_supabase:
            return self._http_json(
                "POST",
                f"{self._supabase_url}/auth/v1/token?grant_type=password",
                {
                    "apikey": self._supabase_anon_key,
                    "Content-Type": "application/json",
                },
                {"email": email, "password": password},
            )

        for token, user in self._local_users.items():
            if user["email"].lower() == email.lower():
                # Check hashed password for user created locally, or raw password for default users
                if "password_hash" in user:
                    if bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
                        return {"access_token": token, "user": {"id": user["user_id"], "email": user["email"]}}
                elif "password" in user and user["password"] == password:
                    return {"access_token": token, "user": {"id": user["user_id"], "email": user["email"]}}
        raise PermissionError("invalid email or password")

    def reset_password(self, email: str) -> dict:
        if self._use_supabase:
            return self._http_json(
                "POST",
                f"{self._supabase_url}/auth/v1/recover",
                {
                    "apikey": self._supabase_anon_key,
                    "Content-Type": "application/json",
                },
                {"email": email},
            )
        return {"message": f"Local dev mode: reset link simulated for {email}"}

    def resolve_token(self, token: str) -> AuthContext:
        token = token.strip()
        if not token:
            raise PermissionError("missing bearer token")

        if self._use_supabase:
            try:
                user = self._http_json(
                    "GET",
                    f"{self._supabase_url}/auth/v1/user",
                    {
                        "apikey": self._supabase_anon_key,
                        "Authorization": f"Bearer {token}",
                    },
                )
            except error.HTTPError as exc:
                raise PermissionError("invalid token") from exc
            
            # The role might be in app_metadata or user_metadata, default to operator if not present
            role = user.get("app_metadata", {}).get("role", "operator")
            
            return AuthContext(
                user_id=user.get("id", "unknown"),
                email=user.get("email", ""),
                role=role,
                access_token=token,
            )

        local = self._local_users.get(token)
        if local is None:
            raise PermissionError("invalid token")
        return AuthContext(user_id=local["user_id"], email=local["email"], role=local["role"], access_token=token)

    def verify_token(self, token: str) -> AuthContext:
        return self.resolve_token(token)
