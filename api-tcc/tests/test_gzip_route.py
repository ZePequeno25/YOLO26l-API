import gzip
import pytest
from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.testclient import TestClient
from app.core.gzip_route import GzipRoute

# Fixture para configurar o app de teste local com GzipRoute
@pytest.fixture
def gzip_client():
    app = FastAPI()
    app.router.route_class = GzipRoute

    @app.post("/test-raw")
    async def test_raw(request: Request):
        body = await request.body()
        return {"content": body.decode("utf-8")}

    @app.post("/test-form")
    async def test_form(name: str = Form(...), age: int = Form(...)):
        return {"name": name, "age": age}

    @app.post("/test-file")
    async def test_file(file: UploadFile = File(...), model: str = Form(...)):
        content = await file.read()
        return {"filename": file.filename, "content": content.decode("utf-8"), "model": model}

    return TestClient(app)


def test_gzip_raw_body_decompression(gzip_client):
    # 1. Envia requisição compactada com cabeçalho correspondente
    data = b"Hello, this is a gzip compressed message!"
    compressed_data = gzip.compress(data)
    
    response = gzip_client.post(
        "/test-raw",
        content=compressed_data,
        headers={"Content-Encoding": "gzip"}
    )
    
    assert response.status_code == 200
    assert response.json()["content"] == "Hello, this is a gzip compressed message!"


def test_gzip_raw_body_fallback_decompression(gzip_client):
    # 2. Envia requisição compactada SEM o cabeçalho Content-Encoding (teste de fallback por magic bytes)
    data = b"Hello, this is a fallback gzip check!"
    compressed_data = gzip.compress(data)
    
    response = gzip_client.post(
        "/test-raw",
        content=compressed_data
    )
    
    assert response.status_code == 200
    assert response.json()["content"] == "Hello, this is a fallback gzip check!"


def test_gzip_multipart_decompression(gzip_client):
    # 3. Envia requisição multipart convencional para garantir que requests normais continuam funcionando
    response = gzip_client.post(
        "/test-form",
        data={"name": "Alice", "age": 30}
    )
    
    assert response.status_code == 200
    assert response.json() == {"name": "Alice", "age": 30}


def test_gzip_multipart_file_upload(gzip_client):
    # 4. Envia requisição multipart com arquivo para certificar que o stream multipart funciona corretamente
    files = {"file": ("test.txt", b"conteudo do arquivo")}
    data = {"model": "chair"}
    
    response = gzip_client.post(
        "/test-file",
        files=files,
        data=data
    )
    
    assert response.status_code == 200
    assert response.json() == {
        "filename": "test.txt",
        "content": "conteudo do arquivo",
        "model": "chair"
    }
