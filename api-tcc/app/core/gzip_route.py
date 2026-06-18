"""
Custom router module to handle GZIP compressed request payloads.
Automatically decompresses requests before passing them to the application handlers.
"""
import gzip
import logging
from typing import AsyncGenerator, Callable

from fastapi import Request, Response
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


class GzipRequest(Request):
    """
    Custom FastAPI Request subclass that decompresses GZIP-encoded request bodies.
    """
    async def body(self) -> bytes:
        """
        Retrieves the request body, decompressing it if it's GZIP-encoded.
        """
        if not hasattr(self, "_body"):
            chunks = []
            async for chunk in Request.stream(self):
                chunks.append(chunk)
            body = b"".join(chunks)

            content_encoding = self.headers.get("Content-Encoding", "")

            # Detecta Gzip tanto pelo Content-Encoding quanto pelo magic byte inicial (0x1f 0x8b)
            is_gzip = "gzip" in content_encoding.lower() or (
                len(body) >= 2 and body[0] == 0x1f and body[1] == 0x8b
            )

            if is_gzip:
                try:
                    logger.info(
                        "Detectada compressão Gzip no corpo da requisição. Descompactando..."
                    )
                    body = gzip.decompress(body)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error("Falha ao descompactar requisição Gzip: %s", str(e), exc_info=True)

            # pylint: disable=attribute-defined-outside-init
            self._body = body
        return self._body

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """
        Streams the decompressed request body.
        """
        # Garante que a leitura via stream do parser multipart retorne os dados descompactados
        body = await self.body()
        yield body
        yield b""


# pylint: disable=too-few-public-methods
class GzipRoute(APIRoute):
    """
    Custom APIRoute class that uses GzipRequest to automatically handle GZIP requests.
    """
    def get_route_handler(self) -> Callable:
        """
        Returns a route handler wrapper that uses GzipRequest instead of Request.
        """
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            # Substitui o request padrão pelo GzipRequest customizado
            request = GzipRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler
