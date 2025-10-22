from flask import Flask, request, jsonify, render_template
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from datetime import datetime
import os
import re

# Load environment variables
load_dotenv()

# Flask app
app = Flask(__name__)

# Connect to Azure Blob Storage
connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
if not connection_string:
    raise ValueError("Missing AZURE_STORAGE_CONNECTION_STRING in .env")

blob_service_client = BlobServiceClient.from_connection_string(connection_string)

# Constants
CONTAINER_NAME = "lanternfly-images"

# Ensure container exists
try:
    blob_service_client.create_container(CONTAINER_NAME, public_access="blob")
except Exception:
    pass  # Container may already exist


# ---------- ROUTES ----------

@app.route("/")
def index():
    return render_template("index.html")


@app.post("/api/v1/upload")
def upload():
    """Handle image uploads"""
    if "file" not in request.files:
        return jsonify(ok=False, error="No file part"), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify(ok=False, error="No file selected"), 400

    # Validate content type (must be an image)
    if not f.content_type.startswith("image/"):
        return jsonify(ok=False, error="Invalid file type; only images allowed"), 400

    # Sanitize filename
    filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", f.filename)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
    blob_name = f"{timestamp}-{filename}"

    try:
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(f, overwrite=True)

        blob_url = f"{blob_client.url}"
        print(f"✅ Uploaded: {blob_url}")
        return jsonify(ok=True, url=blob_url)

    except Exception as e:
        print(f"❌ Upload error: {e}")
        return jsonify(ok=False, error=str(e)), 500


@app.get("/api/v1/gallery")
def gallery():
    """Return JSON with all image URLs"""
    try:
        container_client = blob_service_client.get_container_client(CONTAINER_NAME)
        blobs = container_client.list_blobs()

        urls = [
            f"https://{blob_service_client.account_name}.blob.core.windows.net/{CONTAINER_NAME}/{b.name}"
            for b in blobs
        ]
        return jsonify(ok=True, gallery=urls)

    except Exception as e:
        print(f"❌ Gallery error: {e}")
        return jsonify(ok=False, error=str(e)), 500


@app.get("/api/v1/health")
def health():
    """Health check"""
    return jsonify(ok=True)


# ---------- MAIN ----------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
