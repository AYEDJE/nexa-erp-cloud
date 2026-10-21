from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import time


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware de protection globale de l'application :
    Injecte les en-têtes HTTP de sécurité contre les attaques XSS, Clickjacking,
    MIME-sniffing et force l'utilisation de canaux sécurisés.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response: Response = await call_next(request)
        process_time = time.time() - start_time

        # En-têtes de sécurité recommandés OWASP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"

        return response
