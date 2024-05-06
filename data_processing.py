from collections import Counter


def convert_duration(duration_ms):
    minutes = duration_ms // 60000
    seconds = (duration_ms % 60000) // 1000
    return f'{minutes}m{seconds}s'


def convert_duration_total(duration_ms):
    hours = duration_ms // 3600000
    minutes = (duration_ms % 3600000) // 60000
    seconds = (duration_ms % 60000) // 1000
    if hours > 0:
        return f'{hours}h{minutes}m{seconds}s'
    return f'{minutes}m{seconds}s'


def calculate_stats(tracks):
    num_tracks = len(tracks)
    total_duration_ms = sum(track['duration_ms'] for track in tracks)
    total_duration = convert_duration_total(total_duration_ms)

    artist_counter = Counter()
    label_counter = Counter()
    genre_counter = Counter()

    for track in tracks:
        artists = track['artists'].split(', ')
        artist_counter.update(artists)
        label_counter[track['label']] += 1
        genre_counter.update(track['genres'])

    sorted_artists = sorted(artist_counter.items(), key=lambda x: x[1], reverse=True)
    sorted_labels = sorted(label_counter.items(), key=lambda x: x[1], reverse=True)
    sorted_genres = sorted(genre_counter.items(), key=lambda x: x[1], reverse=True)

    stats = {
        'number_of_tracks': num_tracks,
        'total_duration': total_duration,
        'artists_sorted_by_appearance': sorted_artists,
        'labels_sorted_by_appearance': sorted_labels,
        'genres_sorted_by_appearance': sorted_genres
    }

    return stats
