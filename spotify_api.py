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
    count = 0
    params = {'limit': 100, 'offset': offset}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f'Error fetching tracks page. Response status code: {response.status_code}, Response: {response.text}')
        return []

    data = response.json()
    tracks = []

    for track_data in data['items']:
        count += 1
        track = track_data.get('track')
        if track is None:
            print(f'Track data is None: {track_data}')
            continue

        print(f'Loading track: {track["name"]}')

        album = track.get('album')
        artists = track.get('artists')
        is_local = track.get('is_local', False)

        if is_local:
            album_id = 'LOCAL_ARTIST'
            artist_names = 'LOCAL_ARTIST'
            artist_ids = ['LOCAL_ARTIST']
        else:
            album_id = album.get('id', 'Unknown') if album else 'Unknown'
            artist_names = ', '.join([artist.get('name', 'Unknown') for artist in artists if artist.get('name') is not None])
            artist_ids = [artist.get('id', 'Unknown') for artist in artists if artist.get('id') is not None]

        tracks.append({
            'name': track.get('name', 'Unknown'),
            'artists': artist_names,
            'popularity': track.get('popularity', 0),
            'duration': convert_duration(track.get('duration_ms', 0)),
            'duration_ms': track.get('duration_ms', 0),
            'album_id': album_id,
            'artist_ids': artist_ids,
            'is_local': is_local
        })

    print(f'Loaded {count} tracks on page {offset // 100 + 1}')
    return tracks


def get_all_tracks(playlist_id, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    url = f'{PLAYLIST_API_URL}{playlist_id}/tracks'
    params = {'limit': 100, 'offset': 0}
    tracks = []
    futures = []

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        print(f'Error fetching playlist tracks. Response: {response.text}')
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
        track['genres'] = [genre for artist_id in track['artist_ids'] for genre in artist_id_to_genres.get(artist_id, [])]
        del track['artist_ids']

    return tracks


def fetch_album_labels(album_ids, headers):
    valid_album_ids = [album_id for album_id in album_ids if album_id != 'LOCAL_ARTIST']

    if not valid_album_ids:
        print(f'No valid album IDs to fetch labels for: {album_ids}')
        return {}

    print(f'Fetching album labels for album IDs: {valid_album_ids}')
    params = {'ids': ','.join(valid_album_ids)}
    response = requests.get(ALBUMS_API_URL, headers=headers, params=params)
    if response.status_code != 200:
        print(f'Error fetching album labels. Response status code: {response.status_code}, Response: {response.text}')
        return {}

    try:
        data = response.json()
        albums = data.get('albums', None)
        if albums is None:
            print(f'No albums found in the response data: {data}')
            return {}

        album_labels = {album_id: 'LOCAL_ARTIST' for album_id in album_ids if album_id == 'LOCAL_ARTIST'}
        for album in albums:
            try:
                album_id = album['id']
                album_name = album['name']
                label = album.get('label', 'Unknown')
                album_labels[album_id] = label
                print(f'Album ID: {album_id}, Album Name: {album_name}, Label: {label}')
            except KeyError as e:
                print(f'KeyError in album: {album}, Error: {e}')

        return album_labels
    except Exception as e:
        print(f'Error fetching album labels. Error: {e}')
        return {}


def fetch_artist_genres(artist_ids, headers):
    params = {'ids': ','.join(artist_ids)}
    response = requests.get(ARTISTS_API_URL, headers=headers, params=params)
    if response.status_code != 200:
        print(f'Error fetching artist genres. Response status code: {response.status_code}, Response: {response.text}')
        return {}

    try:
        data = response.json()
        artists = data.get('artists', [])
        if not artists:
            print(f'No artists found in the response data: {data}')
            return {}

        artist_genres = {}
        for artist in artists:
            try:
                artist_id = artist['id']
                artist_name = artist['name']
                genres = artist.get('genres', [])
                artist_genres[artist_id] = genres
                print(f'Artist ID: {artist_id}, Artist Name: {artist_name}, Genres: {genres}')
            except KeyError as e:
                print(f'KeyError in artist: {artist}, Error: {e}')

        return artist_genres
    except Exception as e:
        print(f'Error fetching artist genres. Error: {e}')
        return {}

