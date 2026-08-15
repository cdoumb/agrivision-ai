"""
Tests des cas limites du service — AgriVision-AI (Binôme A).

Usage :
  pip install pytest httpx
  pytest tests/test_api.py -v
"""
import io
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.api.main import app  # noqa: E402

client = TestClient(app)


def make_valid_jpeg_bytes(size=(100, 100)):
    img = Image.new("RGB", size, color="green")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_classes_returns_ten_in_order():
    r = client.get("/classes")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 10
    assert data[0]["culture"] == "Tomate"
    assert data[9]["culture"] == "Poivron"


def test_predict_valid_image():
    img_bytes = make_valid_jpeg_bytes()
    r = client.post("/predict", files={"file": ("leaf.jpg", img_bytes, "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert "predicted_class" in body
    assert "confidence" in body
    assert "model_version" in body


def test_predict_rejects_bad_content_type():
    r = client.post("/predict", files={"file": ("doc.pdf", b"%PDF-1.4 fake", "application/pdf")})
    assert r.status_code == 400


def test_predict_rejects_empty_file():
    r = client.post("/predict", files={"file": ("empty.jpg", b"", "image/jpeg")})
    assert r.status_code == 400


def test_predict_rejects_oversized_file():
    # 5 Mo + 1 octet, cf. contrat d'interface
    big = b"\xff" * (5 * 1024 * 1024 + 1)
    r = client.post("/predict", files={"file": ("big.jpg", big, "image/jpeg")})
    assert r.status_code == 400


def test_predict_rejects_corrupted_image():
    # Content-Type correct, mais contenu illisible : le vrai piège, un
    # client malveillant ou buggé peut mentir sur le Content-Type.
    fake_image = b"this is not a real jpeg file at all"
    r = client.post("/predict", files={"file": ("fake.jpg", fake_image, "image/jpeg")})
    assert r.status_code == 400


def test_predict_rejects_png_disguised_as_exe_content_type():
    img_bytes = make_valid_jpeg_bytes()
    r = client.post("/predict", files={"file": ("leaf.jpg", img_bytes, "application/octet-stream")})
    assert r.status_code == 400
