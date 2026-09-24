import json
from abc import ABC, abstractmethod
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class SMSProviderError(Exception):
    pass


class SMSProvider(ABC):
    @abstractmethod
    def send_verification_code(self, phone, code):
        """Deliver a verification code without returning provider internals."""


class HttpSMSProvider(SMSProvider):
    def __init__(self, endpoint, token, template_id, timeout_seconds):
        self.endpoint = endpoint
        self.token = token
        self.template_id = template_id
        self.timeout_seconds = timeout_seconds

    def send_verification_code(self, phone, code):
        body = json.dumps(
            {
                "phone": phone,
                "code": code,
                "templateId": self.template_id,
            }
        ).encode("utf-8")
        request = Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                status_code = getattr(response, "status", response.getcode())
                if not 200 <= status_code < 300:
                    raise SMSProviderError("SMS provider rejected the request")
        except SMSProviderError:
            raise
        except (HTTPError, URLError, OSError, ValueError) as error:
            raise SMSProviderError("SMS provider request failed") from error


def get_sms_provider(config):
    if config.get("SMS_PROVIDER", "").casefold() != "http":
        raise SMSProviderError("SMS provider is not configured")

    return HttpSMSProvider(
        endpoint=config["SMS_HTTP_ENDPOINT"],
        token=config["SMS_HTTP_TOKEN"],
        template_id=config["SMS_TEMPLATE_ID"],
        timeout_seconds=config["SMS_TIMEOUT_SECONDS"],
    )
