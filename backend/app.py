from chalice import Chalice, CORSConfig
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# CORS configuration
cors_config = CORSConfig(
    allow_origin=os.getenv("CORS_ALLOW_ORIGIN", "http://localhost:5173"),
    allow_headers=["Content-Type", "X-Client-Id", "X-Session-Id"],
    max_age=600,
    allow_credentials=True,
)

app = Chalice(app_name="syuking")


@app.route("/")
def index():
    return {"message": "Syuking API Server", "version": "0.1.0"}


@app.route("/health", methods=["GET"], cors=cors_config)
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "environment": os.getenv("ENVIRONMENT", "dev")}


@app.route("/api/test", methods=["GET"], cors=cors_config)
def test():
    """Test endpoint with CORS enabled"""
    return {"message": "CORS is working!", "api_version": "0.1.0"}


# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.current_request.json_body
#     # We'll echo the json body back to the user in a 'user' key.
#     return {'user': user_as_json}
#
# See the README documentation for more examples.
#
