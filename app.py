import os
import boto3
import requests
from botocore.config import Config
from flask import Flask, request, jsonify
from flask_cors import CORS  # NEW: Required for browser-to-server communication

if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()

app = Flask(__name__)
CORS(app)

def get_s3_client():
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY:
        raise ValueError("AWS credentials not found in environment variables!")
    
    return boto3.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4")
    )

    
@app.route("/")
def health():
    return "Backend is running 🚀"

@app.route("/ping")
def ping():
    return jsonify({
        "AWS_ACCESS_KEY_ID": bool(os.getenv("AWS_ACCESS_KEY_ID")),
        "AWS_SECRET_ACCESS_KEY": bool(os.getenv("AWS_SECRET_ACCESS_KEY")),
        "AWS_REGION": os.getenv("AWS_REGION"),
        "BUCKET_NAME": os.getenv("BUCKET_NAME")
    })


@app.route("/get-presigned-url", methods=["POST"])
def get_presigned_url():
    """
    NEW: Generates a URL that allows the browser to upload directly to S3.
    """
    data = request.get_json()
    file_name = data.get("file_name")
    
    if not file_name:
        return jsonify({"error": "Missing file_name"}), 400

    try:
        s3 = get_s3_client()
        # We specify ContentType as 'audio/webm' so it matches the browser's Blob
        url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET_NAME, 
                "Key": file_name,
                "ContentType": "audio/webm" 
            },
            ExpiresIn=3600
        )
        return jsonify({"url": url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/upload-local-file", methods=["POST"])
def upload_local_file():
    """Kept for your manual testing/local server uploads."""
    data = request.get_json()
    file_path = data.get("file_path")
    s3_key = data.get("s3_key")
    
    if not file_path or not s3_key:
        return jsonify({"error": "Missing file_path or s3_key"}), 400

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    try:
        s3 = get_s3_client()
        presigned_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": BUCKET_NAME, "Key": s3_key},
            ExpiresIn=900
        )
        with open(file_path, "rb") as f:
            response = requests.put(presigned_url, data=f)
            
        return jsonify({"message": "Upload successful"}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port)
