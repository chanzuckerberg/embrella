import logging
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class ConfluenceConnectionManager:
    def __init__(self, base_url, username, api_token):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, api_token)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

