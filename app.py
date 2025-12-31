"""
Simple Flask API to serve JuanStudio data for Railway deployment.
Reads from the exports/data.json file and serves it via API endpoints.
"""
import os
import json
from flask import Flask, jsonify, send_from_directory
from pathlib import Path

app = Flask(__name__, static_folder='frontend/dist')

# Path to the static data exports
DATA_DIR = Path(__file__).parent / 'frontend' / 'dist' / 'data'

def load_json(filename):
    """Load JSON data from the exports directory."""
    filepath = DATA_DIR / filename
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

@app.route('/')
def index():
    """Serve the frontend."""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'project': 'juanstudio'})

@app.route('/api/pages')
def get_pages():
    """Get all pages data."""
    data = load_json('pages.json')
    if data:
        return jsonify(data)
    return jsonify({'error': 'No data found'}), 404

@app.route('/api/posts')
def get_posts():
    """Get all posts data."""
    data = load_json('posts.json')
    if data:
        return jsonify(data)
    return jsonify({'error': 'No data found'}), 404

@app.route('/api/stats')
def get_stats():
    """Get dashboard stats."""
    data = load_json('dashboard_stats.json')
    if data:
        return jsonify(data)
    return jsonify({'error': 'No data found'}), 404

@app.route('/api/comments')
def get_comments():
    """Get comments data."""
    data = load_json('comments.json')
    if data:
        return jsonify(data)
    return jsonify({'error': 'No data found'}), 404

# Serve static files from frontend/dist
@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
