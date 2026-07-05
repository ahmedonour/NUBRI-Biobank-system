import requests
import json
from datetime import datetime


class PocketBaseAuth:
    def __init__(self, base_url=None):
        self.base_url = base_url or "http://127.0.0.1:8090"
        self.token = None
        self.user = None

    @property
    def _api_url(self):
        return f"{self.base_url}/api"

    def login(self, email, password):
        resp = requests.post(
            f"{self._api_url}/collections/users/auth-with-password",
            json={"identity": email, "password": password},
            timeout=10
        )
        if not resp.ok:
            detail = resp.json().get("message", "Invalid credentials")
            raise PermissionError(f"Login failed: {detail}")

        data = resp.json()
        self.token = data["token"]
        self.user = data["record"]
        return self.user

    def signup(self, email, password, password_confirm=None, **extra):
        payload = {
            "email": email,
            "password": password,
            "passwordConfirm": password_confirm or password,
            **extra
        }
        resp = requests.post(
            f"{self._api_url}/collections/users/records",
            json=payload,
            timeout=10
        )
        if not resp.ok:
            detail = resp.json().get("message", "Signup failed")
            raise PermissionError(f"Signup failed: {detail}")
        return resp.json()

    def logout(self):
        self.token = None
        self.user = None

    @property
    def is_authenticated(self):
        return self.token is not None and self.user is not None

    def verify_token(self):
        if not self.token:
            return False
        try:
            resp = requests.get(
                f"{self._api_url}/collections/users/auth-refresh",
                headers=self._headers,
                timeout=10
            )
            if resp.ok:
                data = resp.json()
                self.token = data["token"]
                self.user = data["record"]
                return True
            return False
        except requests.RequestException:
            return False

    @property
    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get_user_email(self):
        return self.user.get("email", "unknown") if self.user else ""

    def get_user_name(self):
        return self.user.get("name", self.get_user_email()) if self.user else ""

    def request(self, method, path, **kwargs):
        kwargs.setdefault("headers", {}).update(self._headers)
        if "timeout" not in kwargs:
            kwargs["timeout"] = 10
        resp = requests.request(method, f"{self._api_url}/{path}", **kwargs)
        if resp.status_code == 401:
            self.logout()
            raise PermissionError("Session expired. Please sign in again.")
        return resp
