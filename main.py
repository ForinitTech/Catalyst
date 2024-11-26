import os
import tempfile
import logging
import pyimgur
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Imgur Client ID, Instagram user ID, and Access Token
IMGUR_CLIENT_ID = os.getenv("IMGUR_CLIENT_ID")
IG_USER_ID = os.getenv("IG_USER_ID")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")

# Upload to Imgur
def upload_to_imgur(local_file_path):
    try:
        im = pyimgur.Imgur(IMGUR_CLIENT_ID)
        uploaded_image = im.upload_image(local_file_path, title="Uploaded via Cloud Function")
        return uploaded_image.link
    except Exception as e:
        logger.error(f"Failed to upload to Imgur: {e}")
        return None

# Upload to Instagram
def upload_media_to_instagram(image_url, caption):
    url = f"https://graph.facebook.com/v16.0/{IG_USER_ID}/media"
    params = {"image_url": image_url, "caption": caption, "access_token": INSTAGRAM_ACCESS_TOKEN}
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return response.json().get("id")
    else:
        logger.error(f"Failed to upload media: {response.json()}")
        return None

# Publish Media
def publish_media(media_id):
    url = f"https://graph.facebook.com/v16.0/{IG_USER_ID}/media_publish"
    params = {"creation_id": media_id, "access_token": INSTAGRAM_ACCESS_TOKEN}
    response = requests.post(url, params=params)
    if response.status_code == 200:
        return "Media published successfully!"
    else:
        logger.error(f"Failed to publish media: {response.json()}")
        return f"Failed to publish media: {response.json()}"

# Enable CORS headers
def enable_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'  # Update with real frontend domain
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.route('/post_to_instagram_via_api', methods=['POST'])
def post_to_instagram_via_api(request):
    try:
        if request.method == 'OPTIONS':  # Handle preflight requests
            return '', 204  # No content for OPTIONS method

        if request.method != 'POST':
            return jsonify({"message": "Only POST requests are allowed"}), 405

        caption = request.form.get('caption')
        file = request.files['media']
        if not file or not caption:
            return jsonify({"message": "Missing caption or media file"}), 400

        # Validate file type
        file_type = file.content_type
        if file_type not in ['image/jpeg', 'image/png']:
            return jsonify({"message": "Invalid file type. Only JPEG and PNG are allowed."}), 400

        # Save the uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file_path = temp_file.name
            file.save(file_path)

        # Upload the image to Imgur
        uploaded_image_url = upload_to_imgur(file_path)
        os.remove(file_path)  # Clean up the temp file
        if not uploaded_image_url:
            return jsonify({"message": "Failed to upload image to Imgur"}), 500

        # Upload media to Instagram
        media_id = upload_media_to_instagram(uploaded_image_url, caption)
        if not media_id:
            return jsonify({"message": "Failed to upload media to Instagram"}), 500

        # Publish media on Instagram
        result = publish_media(media_id)
        return jsonify({"message": "Media uploaded and published successfully!"})

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"message": "An error occurred", "error": str(e)}), 500

# Apply CORS headers after every request
@app.after_request
def after_request(response):
    print(response.headers) 
    return enable_cors(response)

if __name__ == "__main__":
    app.run(debug=True)
