from flask import Flask, Response, request
from utils import *

app = Flask(__name__)

@app.route('/stream/<path:cam_url>')
def video_feed(cam_url):
    """
    Returns a augmented video feed from the input from camera url provided.
    """
    return Response(generate_feed(cam_url), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/snapshot/<path:cam_url>')
def snapshot(cam_url):
    """
    Returns a augmented snapshot from the input from camera url provided.
    """
    return next(generate_snapshot(cam_url))
    
if __name__ == "__main__":
    app.run(host='', port=27100)
    