import logging
logger = logging.getLogger("app")

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        logger.info(
            "REQUEST %s %s USER=%s",
            request.method,
            request.path,
            request.user if request.user.is_authenticated else "anon"
        )
        return self.get_response(request)
