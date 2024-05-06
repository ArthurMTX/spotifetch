import requests
import base64
import os
from os.path import join, dirname
from dotenv import load_dotenv
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_processing import convert_duration

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')
AUTH_URL = 'https://accounts.spotify.com/api/token'
PLAYLIST_API_URL = 'https://api.spotify.com/v1/playlists/'
ALBUMS_API_URL = 'https://api.spotify.com/v1/albums'
ARTISTS_API_URL = 'https://api.spotify.com/v1/artists'


def get_access_token():
    auth_header = base64.b64encode(f'{CLIENT_ID}:{CLIENT_SECRET}'.encode('utf-8')).decode('utf-8')
    headers = {'Authorization': f'Basic {auth_header}'}
    data = {'grant_type': 'client_credentials'}
    response = requests.post(AUTH_URL, headers=headers, data=data)
    response_data = response.json()
    if 'access_token' in response_data:
        return response_data['access_token']
    else:
        raise Exception('Failed to get access token')


def fetch_tracks_page(url, headers, offset):
    params = {'limit': 100, 'offset': offset}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        return []
    data = response.json()
    tracks = [{
        'name': track['track']['name'],
        'artists': ', '.join([artist['name'] for artist in track['track']['artists']]),
        'popularity': track['track']['popularity'],
        'duration': convert_duration(track['track']['duration_ms']),
        'duration_ms': track['track']['duration_ms'],
        'album_id': track['track']['album']['id'],
        'artist_ids': [artist['id'] for artist in track['track']['artists']],
    } for track in data['items']]
    return tracks


def get_all_tracks(playlist_id, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'{PLAYLIST_API_URL}{playlist_id}/tracks'
    params = {'limit': 100, 'offset': 0}
    tracks = []
    futures = []

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        return []
    data = response.json()
    tracks.extend(fetch_tracks_page(url, headers, 0))
    total_tracks = data['total']

    remaining_pages = (total_tracks - 100) // 100 + 1

    with ThreadPoolExecutor(max_workers=10) as executor:
        for page in range(1, remaining_pages + 1):
            offset = page * 100
            futures.append(executor.submit(fetch_tracks_page, url, headers, offset))

        for future in as_completed(futures):
            tracks.extend(future.result())

    album_id_to_label = defaultdict(str)
    album_ids = list({track['album_id'] for track in tracks})
    for i in range(0, len(album_ids), 20):
        batch_ids = album_ids[i:i + 20]
        album_id_to_label.update(fetch_album_labels(batch_ids, headers))

    artist_id_to_genres = defaultdict(list)
    artist_ids = list({artist_id for track in tracks for artist_id in track['artist_ids']})
    for i in range(0, len(artist_ids), 50):
        batch_ids = artist_ids[i:i + 50]
        artist_id_to_genres.update(fetch_artist_genres(batch_ids, headers))

    for track in tracks:
        track['label'] = album_id_to_label[track['album_id']]
        del track['album_id']

    for track in tracks:
        track['genres'] = [genre for artist_id in track['artist_ids'] for genre in artist_id_to_genres[artist_id]]
        del track['artist_ids']

    return tracks


def fetch_album_labels(album_ids, headers):
    params = {'ids': ','.join(album_ids)}
    response = requests.get(ALBUMS_API_URL, headers=headers, params=params)
    if response.status_code != 200:
        return {}
    data = response.json()
    return {album['id']: album['label'] for album in data['albums']}


def fetch_artist_genres(artist_ids, headers):
    params = {'ids': ','.join(artist_ids)}
    response = requests.get(ARTISTS_API_URL, headers=headers, params=params)
    if response.status_code != 200:
        return {}
    data = response.json()
    return {artist['id']: artist['genres'] for artist in data['artists']}
