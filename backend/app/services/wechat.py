from dataclasses import dataclass
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


WECHAT_CODE_EXCHANGE_ENDPOINT = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_HTTP_RESPONSE_LIMIT = 64 * 1024


class WechatProviderError(Exception):
    code = "WECHAT_PROVIDER_UNAVAILABLE"


class WechatAuthorizationError(WechatProviderError):
    code = "WECHAT_AUTHORIZATION_FAILED"


class WechatProviderResponseError(WechatProviderError):
    code = "WECHAT_PROVIDER_RESPONSE_INVALID"


@dataclass(frozen=True)
class WechatIdentity:
    openid: str
    unionid: str | None = None


class WechatAuthProvider:
    def __init__(self, *, app_id, app_secret, timeout_seconds, opener=None):
        self.app_id = _required_text(app_id)
        self.app_secret = _required_text(app_secret)
        try:
            self.timeout_seconds = int(timeout_seconds)
        except (TypeError, ValueError) as error:
            raise WechatProviderError("Wechat provider configuration is invalid") from error
        if not self.app_id or not self.app_secret or self.timeout_seconds <= 0:
            raise WechatProviderError("Wechat provider configuration is invalid")
        self._opener = opener or urlopen

    def exchange_code(self, code):
        code = _required_text(code)
        if not code:
            raise WechatAuthorizationError("Wechat authorization code is invalid")

        query = urlencode(
            {
                "appid": self.app_id,
                "secret": self.app_secret,
                "code": code,
                "grant_type": "authorization_code",
            }
        )
        request = Request(
            f"{WECHAT_CODE_EXCHANGE_ENDPOINT}?{query}",
            headers={"Accept": "application/json", "User-Agent": "Tonglvji-WechatAuth/1.0"},
            method="GET",
        )

        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                status_code = getattr(response, "status", response.getcode())
                body = response.read(WECHAT_HTTP_RESPONSE_LIMIT)
        except HTTPError as error:
            if 400 <= error.code < 500:
                raise WechatAuthorizationError("Wechat authorization was rejected") from error
            raise WechatProviderError("Wechat provider is unavailable") from error
        except (TimeoutError, URLError, OSError, ValueError) as error:
            raise WechatProviderError("Wechat provider is unavailable") from error

        if not 200 <= status_code < 300:
            raise WechatProviderError("Wechat provider is unavailable")
        payload = _parse_provider_payload(body)
        if payload.get("errcode") not in (None, 0, "0"):
            raise WechatAuthorizationError("Wechat authorization was rejected")

        openid = _identity_value(payload.get("openid"))
        if not openid:
            raise WechatProviderResponseError("Wechat provider response is missing openid")
        unionid = _identity_value(payload.get("unionid"))
        return WechatIdentity(openid=openid, unionid=unionid)


def get_wechat_auth_provider(config):
    return WechatAuthProvider(
        app_id=config["WECHAT_APP_ID"],
        app_secret=config["WECHAT_APP_SECRET"],
        timeout_seconds=config["WECHAT_TIMEOUT_SECONDS"],
    )


def _required_text(value):
    return value.strip() if isinstance(value, str) else ""


def _identity_value(value):
    normalized = _required_text(value)
    if not normalized:
        return None
    if len(normalized) > 128:
        raise WechatProviderResponseError("Wechat provider identity is invalid")
    return normalized


def _parse_provider_payload(body):
    if not isinstance(body, bytes) or not body:
        raise WechatProviderResponseError("Wechat provider response is empty")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WechatProviderResponseError("Wechat provider response is malformed") from error
    if not isinstance(payload, dict):
        raise WechatProviderResponseError("Wechat provider response is malformed")
    return payload
