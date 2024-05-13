import requests
import base64
import os
from os.path import join, dirname
from dotenv import load_dotenv
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from data_processing import calculate_stats, convert_duration

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
    tracks = []

    for track_data in data['items']:
        track = track_data.get('track')
        if track is None:
            continue

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
            'album_cover': album.get('images')[0]['url'] if album and album.get('images') else '',
            'album_name': album.get('name', 'Unknown') if album else 'Unknown',
            'is_local': is_local
        })

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
    album_id_to_name = defaultdict(str)
    album_ids = list({track['album_id'] for track in tracks})
    for i in range(0, len(album_ids), 20):
        batch_ids = album_ids[i:i + 20]
        album_labels, album_names = fetch_album_labels(batch_ids, headers)
        album_id_to_label.update(album_labels)
        album_id_to_name.update(album_names)

    artist_id_to_genres = defaultdict(list)
    artist_ids = list({artist_id for track in tracks for artist_id in track['artist_ids']})
    for i in range(0, len(artist_ids), 50):
        batch_ids = artist_ids[i:i + 50]
        artist_id_to_genres.update(fetch_artist_genres(batch_ids, headers))

    for track in tracks:
        track['label'] = album_id_to_label[track['album_id']]
        track['album'] = album_id_to_name[track['album_id']]
        del track['album_id']

    for track in tracks:
        track['genres'] = [genre for artist_id in track['artist_ids'] for genre in
                           artist_id_to_genres.get(artist_id, [])]
        del track['artist_ids']

    return tracks


def fetch_album_labels(album_ids, headers):
    valid_album_ids = [album_id for album_id in album_ids if album_id != 'LOCAL_ARTIST']

    if not valid_album_ids:
        return {}

    params = {'ids': ','.join(valid_album_ids)}
    response = requests.get(ALBUMS_API_URL, headers=headers, params=params)
    if response.status_code != 200:
        return {}

    data = response.json()
    albums = data.get('albums', None)
    if albums is None:
        return {}

    album_labels = {album_id: 'LOCAL_ARTIST' for album_id in album_ids if album_id == 'LOCAL_ARTIST'}
    album_names = {}
    for album in albums:
        album_id = album['id']
        label = album.get('label', 'Unknown')
        name = album.get('name', 'Unknown')
        album_labels[album_id] = label
        album_names[album_id] = name

    return album_labels, album_names


def fetch_artist_genres(artist_ids, headers):
    params = {'ids': ','.join(artist_ids)}
    response = requests.get(ARTISTS_API_URL, headers=headers, params=params)
    if response.status_code != 200:
        return {}

    data = response.json()
    artists = data.get('artists', [])
    if not artists:
        return {}

    artist_genres = {}
    for artist in artists:
        artist_id = artist['id']
        genres = artist.get('genres', [])
        artist_genres[artist_id] = genres

    return artist_genres


def get_owner_image(owner_data):
    images = owner_data.get('images', [])
    if images:
        return images[0]['url']
    return ''


def get_playlist_info(playlist_id):
    access_token = get_access_token()
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'{PLAYLIST_API_URL}{playlist_id}', headers=headers)

    if response.status_code == 200:
        playlist_data = response.json()
        tracks = get_all_tracks(playlist_id, access_token)
        stats = calculate_stats(tracks)

        owner_image = get_owner_image(playlist_data['owner'])

        result = {
            'name': playlist_data['name'],
            'description': playlist_data['description'],
            'followers': playlist_data['followers']['total'],
            'url': playlist_data['external_urls']['spotify'],
            'owner': playlist_data['owner']['display_name'],
            'owner_image': owner_image,
            'image': playlist_data['images'][0]['url'],
            'tracks': [
                {
                    'name': track['name'],
                    'artists': track['artists'],
                    'popularity': track['popularity'],
                    'duration': track['duration'],
                    'label': track['label'],
                    'album_name': track['album_name'],
                    'album_cover': track['album_cover'],
                    'genres': track['genres'],
                    'is_local': track['is_local']
                }
                for track in tracks
            ],
            'stats': stats
        }
        return result
    else:
        return {}

