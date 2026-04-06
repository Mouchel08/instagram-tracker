"""
Instagram Graph API client.
Handles authentication, requests, pagination, and rate limiting.
"""

import time
import requests
from config import ACCESS_TOKEN, USER_ID, BASE_URL, GRAPH_URL


class InstagramAPIError(Exception):
    pass


class InstagramAPI:
    def __init__(self, access_token=None, user_id=None):
        self.access_token = access_token or ACCESS_TOKEN
        self.user_id = user_id or USER_ID
        self._validate_credentials()

    def _validate_credentials(self):
        if not self.access_token:
            raise InstagramAPIError(
                "No access token found. Set INSTAGRAM_ACCESS_TOKEN in your .env file.\n"
                "See README.md for setup instructions."
            )
        if not self.user_id:
            # Try to fetch user ID automatically
            self.user_id = self._fetch_user_id()

    def _fetch_user_id(self):
        resp = self._get(f"{BASE_URL}/me", params={"fields": "id,username"})
        uid = resp.get("id")
        if not uid:
            raise InstagramAPIError("Could not fetch Instagram user ID. Check your access token.")
        print(f"Auto-detected Instagram User ID: {uid} (@{resp.get('username', '?')})")
        return uid

    def _get(self, url, params=None, retries=3):
        params = params or {}
        params["access_token"] = self.access_token

        for attempt in range(retries):
            try:
                resp = requests.get(url, params=params, timeout=30)
                data = resp.json()

                if "error" in data:
                    err = data["error"]
                    code = err.get("code", 0)
                    # Rate limit hit — back off
                    if code in (4, 17, 32, 613):
                        wait = 60 * (attempt + 1)
                        print(f"Rate limit hit. Waiting {wait}s...")
                        time.sleep(wait)
                        continue
                    raise InstagramAPIError(f"API error {code}: {err.get('message', err)}")

                return data

            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(5)
                    continue
                raise InstagramAPIError(f"Request failed: {e}")

        raise InstagramAPIError("Max retries exceeded")

    def get_all_media(self, fields: str, limit: int = 100) -> list[dict]:
        """Fetch all media using cursor-based pagination."""
        all_media = []
        url = f"{BASE_URL}/{self.user_id}/media"
        params = {"fields": fields, "limit": limit}

        while url:
            data = self._get(url, params=params)
            items = data.get("data", [])
            all_media.extend(items)
            print(f"  Fetched {len(all_media)} posts so far...", end="\r")

            # Follow pagination cursors
            paging = data.get("paging", {})
            next_url = paging.get("next")
            if next_url:
                # next URL already has all params embedded
                url = next_url
                params = {}
            else:
                url = None

        print(f"\n  Total posts fetched: {len(all_media)}")
        return all_media

    def get_media_insights(self, media_id: str, media_type: str) -> dict:
        """Fetch insights for a single media object."""
        from config import PHOTO_CAROUSEL_METRICS, VIDEO_REEL_METRICS

        if media_type in ("VIDEO", "REELS"):
            metrics = VIDEO_REEL_METRICS
        else:
            metrics = PHOTO_CAROUSEL_METRICS

        url = f"{BASE_URL}/{media_id}/insights"
        try:
            data = self._get(url, params={"metric": metrics})
            result = {}
            for item in data.get("data", []):
                result[item["name"]] = item.get("values", [{}])[-1].get("value", item.get("value", 0))
            return result
        except InstagramAPIError:
            # Some older posts don't support all metrics — return empty
            return {}

    def get_account_info(self) -> dict:
        """Fetch basic account profile info."""
        fields = "id,username,name,biography,followers_count,follows_count,media_count,profile_picture_url,website"
        return self._get(f"{BASE_URL}/{self.user_id}", params={"fields": fields})

    def get_account_insights(self, period: str = "day", since: str = None, until: str = None) -> dict:
        """Fetch account-level insights."""
        from config import ACCOUNT_METRICS
        params = {
            "metric": ACCOUNT_METRICS,
            "period": period,
        }
        if since:
            params["since"] = since
        if until:
            params["until"] = until

        url = f"{BASE_URL}/{self.user_id}/insights"
        try:
            return self._get(url, params=params)
        except InstagramAPIError:
            return {}

    def exchange_for_long_lived_token(self, short_token: str) -> dict:
        """Exchange a short-lived token for a 60-day long-lived token."""
        from config import APP_ID, APP_SECRET
        params = {
            "grant_type": "ig_exchange_token",
            "client_secret": APP_SECRET,
            "access_token": short_token,
        }
        return self._get(f"{GRAPH_URL}/oauth/access_token", params=params)

    def refresh_long_lived_token(self) -> dict:
        """Refresh a long-lived token before it expires."""
        params = {
            "grant_type": "ig_refresh_token",
            "access_token": self.access_token,
        }
        return self._get(f"{GRAPH_URL}/refresh_access_token", params=params)
