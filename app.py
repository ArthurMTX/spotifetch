from flask import Flask, jsonify
import requests
import time

from data_processing import calculate_stats
from spotify_api import get_access_token, PLAYLIST_API_URL, get_all_tracks

app = Flask(__name__)


@app.route('/playlist/<playlist_id>', methods=['GET'])
def get_playlist_info(playlist_id):
    start_time = time.time()
    access_token = get_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'{PLAYLIST_API_URL}{playlist_id}', headers=headers)

    if response.status_code == 200:
        playlist_data = response.json()
        tracks = get_all_tracks(playlist_id, access_token)
        stats = calculate_stats(tracks)
        result = {
            'name': playlist_data['name'],
            'description': playlist_data['description'],
            'followers': playlist_data['followers']['total'],
            'url': playlist_data['external_urls']['spotify'],
            'owner': playlist_data['owner']['display_name'],
            'image': playlist_data['images'][0]['url'],
            'tracks': [
                {
                    'name': track['name'],
                    'artists': track['artists'],
                    'popularity': track['popularity'],
                    'duration': track['duration'],
                    'label': track['label']
                } for track in tracks
            ],
            'stats': stats,
            'request_time_seconds': round(time.time() - start_time, 2)
        }
        return jsonify(result)
    else:
        return jsonify({'error': 'Could not fetch playlist data',
                        'request_time_seconds': round(time.time() - start_time, 2)}), response.status_code


@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run(debug=True)
