import gzip
import logging
from collections.abc import AsyncGenerator, Callable
from fastapi import Request, Response
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)

class GzipRequest(Request):
    async def body(self) -> bytes:
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
                    logger.info("Detectada compressão Gzip no corpo da requisição. Descompactando...")
                    body = gzip.decompress(body)
                except Exception as e:
                    logger.error(f"Falha ao descompactar requisição Gzip: {e}", exc_info=True)
            
            self._body = body
        return self._body

    async def stream(self) -> AsyncGenerator[bytes, None]:
        # Garante que a leitura via stream do parser multipart retorne os dados descompactados
        body = await self.body()
        yield body
        yield b""


class GzipRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            # Substitui o request padrão pelo GzipRequest customizado
            request = GzipRequest(request.scope, request.receive)
            return await original_route_handler(request)

        return custom_route_handler
