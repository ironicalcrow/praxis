import sys
import types

# Mock lzma for torchvision in environments missing _lzma C extension
if 'lzma' not in sys.modules:
    mock_lzma = types.ModuleType('lzma')
    mock_lzma.LZMAError = Exception
    mock_lzma.open = lambda *args, **kwargs: None
    sys.modules['lzma'] = mock_lzma

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Praxis server is running"}

def test_health_check_returns_dict():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "db" in data
    assert "redis" in data

def test_docs_endpoint():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

def test_unauthorized_access():
    response = client.get("/api/cv/uploads")
    assert response.status_code in [401, 403, 404]
