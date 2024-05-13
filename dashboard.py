import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
from dash import dash_table
import plotly.express as px
import plotly.graph_objects as go
from colorthief import ColorThief
from io import BytesIO
import requests
from spotify_api import get_playlist_info


def init_dashboard(server):
    app = dash.Dash(
        __name__,
        server=server,
        routes_pathname_prefix='/dash/',
        external_stylesheets=[dbc.themes.BOOTSTRAP]
    )

    def get_dominant_color(image_url):
        try:
            response = requests.get(image_url)
            color_thief = ColorThief(BytesIO(response.content))
            return color_thief.get_color(quality=1)
        except Exception as e:
            print(f'Error getting dominant color: {e}')
            return 0, 0, 0

    app.layout = dbc.Container([
        html.H1('Interactive Spotify Playlist Dashboard', className='mb-4 mt-4 text-center'),

        dbc.Row([
            dbc.Col([
                html.Label('Enter Playlist ID:'),
                dbc.Input(id='playlist-id-input', placeholder='Enter Spotify Playlist ID',
                          type='text', value='37i9dQZF1DX0XUsuxWHRQd', className='mb-3')
            ], width=6),
            dbc.Col([
                dbc.Button('Update Dashboard', id='update-button', n_clicks=0,
                           color='primary', className='mb-3 mt-4')
            ], width=3)
        ], className='mb-4'),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Playlist Information', className='card-title'),
                        dcc.Loading(html.Div(id='playlist-info', children=[]), type='default')
                    ], id='playlist-info-body')
                ], className='mb-4', id='playlist-info-card')
            ], width=12)
        ]),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Top Artists', className='card-title'),
                        dcc.Loading(dcc.Graph(id='top-artists-chart'), type='default')
                    ])
                ], className='mb-4')
            ], width=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Top Genres', className='card-title'),
                        dcc.Loading(dcc.Graph(id='top-genres-chart'), type='default')
                    ])
                ], className='mb-4')
            ], width=6)
        ]),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Top Labels', className='card-title'),
                        dcc.Loading(dcc.Graph(id='top-labels-chart'), type='default')
                    ])
                ], className='mb-4')
            ], width=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Track Distribution by Popularity', className='card-title'),
                        dcc.Loading(dcc.Graph(id='track-popularity-chart'), type='default')
                    ])
                ], className='mb-4')
            ], width=6)
        ]),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Track List', className='card-title'),
                        dcc.Loading(dash_table.DataTable(
                            id='track-list',
                            columns=[
                                {'name': 'Cover', 'id': 'album_cover', 'presentation': 'markdown'},
                                {'name': 'Name', 'id': 'name'},
                                {'name': 'Artists', 'id': 'artists'},
                                {'name': 'Album', 'id': 'album_name'},
                                {'name': 'Popularity', 'id': 'popularity'},
                                {'name': 'Duration', 'id': 'duration'},
                            ],
                            data=[],
                            sort_action='native',
                            style_cell={'padding': '5px', 'textAlign': 'left', 'fontFamily': 'Arial', 'fontSize': '14px'},
                            style_header={
                                'backgroundColor': 'rgb(230, 230, 230)',
                                'fontWeight': 'bold',
                                'fontFamily': 'Arial',
                                'fontSize': '16px'
                            }
                        ))
                    ])
                ], className='mb-4')
            ], width=12)
        ])
    ], fluid=True)

    @app.callback(
        [
            Output('playlist-info', 'children'),
            Output('top-artists-chart', 'figure'),
            Output('top-genres-chart', 'figure'),
            Output('top-labels-chart', 'figure'),
            Output('track-popularity-chart', 'figure'),
            Output('track-list', 'data'),
            Output('track-list', 'columns'),
            Output('playlist-info-body', 'style')
        ],
        [Input('update-button', 'n_clicks')],
        [State('playlist-id-input', 'value')]
    )
    def update_dashboard(n_clicks, playlist_id):
        if not playlist_id:
            return ['', go.Figure(), go.Figure(), go.Figure(), go.Figure(), [], {}]

        result = get_playlist_info(playlist_id)

        print(result)

        if not result:
            return ['Playlist not found', go.Figure(), go.Figure(), go.Figure(), go.Figure(), [], {}]

        # Playlist Information
        dominant_color = get_dominant_color(result['image'])
        dominant_color_rgb = f'rgb({dominant_color[0]},{dominant_color[1]},{dominant_color[2]})'
        playlist_info_style = {'backgroundColor': dominant_color_rgb, 'color': 'white', 'padding': '10px'}

        playlist_info = [
            html.Img(src=result['image'], style={'width': '50%', 'margin-bottom': '20px'}),
            html.H3(result['name'], style={'textAlign': 'center'}),
            html.P('Description: ' + result['description']),
            html.P('Followers: ' + str(result['followers'])),
            html.P('Owner: ' + result['owner']),
            html.A('Open in Spotify', href=result['url'], target='_blank', className='btn btn-primary'),
            html.Img(src=result['owner_image'], style={'width': '25px', 'borderRadius': '50%', 'margin-top': '10px'})
        ]

        # Top Artists Chart
        artists = result['stats']['artists_sorted_by_appearance'][:10]
        fig_artists = px.bar(
            x=[artist[0] for artist in artists],
            y=[artist[1] for artist in artists],
            text=[artist[1] for artist in artists],
            labels={'x': 'Artists', 'y': 'Count'},
            title='Top 10 Artists'
        )
        fig_artists.update_traces(marker_color='dodgerblue', textposition='auto')

        # Top Genres Chart
        genres = result['stats']['genres_sorted_by_appearance'][:10]
        fig_genres = px.bar(
            x=[genre[0] for genre in genres],
            y=[genre[1] for genre in genres],
            text=[genre[1] for genre in genres],
            labels={'x': 'Genres', 'y': 'Count'},
            title='Top 10 Genres'
        )
        fig_genres.update_traces(marker_color='darkorange', textposition='auto')

        # Top Labels Chart
        labels = result['stats']['labels_sorted_by_appearance'][:10]
        fig_labels = px.bar(
            x=[label[0] for label in labels],
            y=[label[1] for label in labels],
            text=[label[1] for label in labels],
            labels={'x': 'Labels', 'y': 'Count'},
            title='Top 10 Labels'
        )
        fig_labels.update_traces(marker_color='darkgreen', textposition='auto')

        # Track Popularity Chart
        fig_popularity = px.histogram(
            [track['popularity'] for track in result['tracks']],
            nbins=20,
            labels={'value': 'Popularity', 'count': 'Count'},
            title='Track Distribution by Popularity'
        )
        fig_popularity.update_traces(marker_color='crimson')

        track_list_data = [
            {
                'album_cover': f'![Cover]({track["album_cover"]})',
                'name': track['name'],
                'artists': track['artists'],
                'album_name': track['album_name'],
                'popularity': track['popularity'],
                'duration': track['duration']
            }
            for track in result['tracks']
        ]

        track_list_columns = [
            {'name': 'Cover', 'id': 'album_cover', 'presentation': 'markdown'},
            {'name': 'Name', 'id': 'name'},
            {'name': 'Artists', 'id': 'artists'},
            {'name': 'Album', 'id': 'album_name'},
            {'name': 'Popularity', 'id': 'popularity'},
            {'name': 'Duration', 'id': 'duration'}
        ]

        return [playlist_info, fig_artists, fig_genres, fig_labels, fig_popularity, track_list_data, track_list_columns,
                playlist_info_style]

    return app
