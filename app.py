import requests
import time
from flask import Flask, jsonify
from data_processing import calculate_stats
from spotify_api import get_access_token, PLAYLIST_API_URL, get_all_tracks
from flask import render_template
import plotly.graph_objects as go
import plotly.offline as po

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
                    'label': track['label'],
                    'is_local': track['is_local'],
                } for track in tracks
            ],
            'stats': stats,
            'request_time_seconds': round(time.time() - start_time, 2)
        }
        return jsonify(result)
    else:
        return jsonify({'error': 'Could not fetch playlist data',
                        'request_time_seconds': round(time.time() - start_time, 2)}), response.status_code


@app.route('/playlist/<playlist_id>/charts', methods=['GET'])
def get_playlist_charts(playlist_id):
    response = get_playlist_info(playlist_id)
    result = response.get_json()

    # Infos générales
    fig_info = go.Figure(data=[go.Table(
        header=dict(values=['Name', 'Description', 'Followers', 'Owner'],
                    fill_color='paleturquoise',
                    align='left'),
        cells=dict(values=[result['name'], result['description'], result['followers'], result['owner']],
                   fill_color='lavender',
                   align='left'))
    ])
    fig_info_html = po.plot(fig_info, output_type='div', include_plotlyjs=False)

    # Top 10 artistes
    artists = result['stats']['artists_sorted_by_appearance'][:20]
    fig_artists = go.Figure(data=[go.Bar(
        x=[artist[0] for artist in artists],
        y=[artist[1] for artist in artists],
        text=[artist[1] for artist in artists],
        textposition='auto',
    )])
    fig_artists_html = po.plot(fig_artists, output_type='div', include_plotlyjs=False)

    # Top 10 labels
    labels = result['stats']['labels_sorted_by_appearance'][:20]
    fig_labels = go.Figure(data=[go.Bar(
        x=[label[0] for label in labels],
        y=[label[1] for label in labels],
        text=[label[1] for label in labels],
        textposition='auto',
    )])
    fig_labels_html = po.plot(fig_labels, output_type='div', include_plotlyjs=False)

    # Top 10 genres
    genres = result['stats']['genres_sorted_by_appearance'][:20]
    fig_genres = go.Figure(data=[go.Bar(
        x=[genre[0] for genre in genres],
        y=[genre[1] for genre in genres],
        text=[genre[1] for genre in genres],
        textposition='auto',
    )])
    fig_genres_html = po.plot(fig_genres, output_type='div', include_plotlyjs=False)

    return render_template('charts.html', fig_info_html=fig_info_html, fig_artists_html=fig_artists_html, fig_labels_html=fig_labels_html, fig_genres_html=fig_genres_html)


if __name__ == '__main__':
    app.run(debug=True)
