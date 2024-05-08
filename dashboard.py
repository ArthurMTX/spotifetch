import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from spotify_api import get_playlist_info


def init_dashboard(server):
    app = dash.Dash(
        __name__,
        server=server,
        routes_pathname_prefix='/dash/',
        external_stylesheets=[dbc.themes.BOOTSTRAP]
    )

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
                        html.Div(id='playlist-info', children=[]),
                    ])
                ], className='mb-4')
            ], width=4),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Top Artists', className='card-title'),
                        dcc.Graph(id='top-artists-chart'),
                    ])
                ], className='mb-4')
            ], width=4),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Top Genres', className='card-title'),
                        dcc.Graph(id='top-genres-chart'),
                    ])
                ], className='mb-4')
            ], width=4)
        ]),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Top Labels', className='card-title'),
                        dcc.Graph(id='top-labels-chart'),
                    ])
                ], className='mb-4')
            ], width=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Track Distribution by Popularity', className='card-title'),
                        dcc.Graph(id='track-popularity-chart'),
                    ])
                ], className='mb-4')
            ], width=6)
        ]),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5('Track List', className='card-title'),
                        html.Div(id='track-list', children=[]),
                    ])
                ], className='mb-4')
            ])
        ])
    ], fluid=True)

    @app.callback(
        [
            Output('playlist-info', 'children'),
            Output('top-artists-chart', 'figure'),
            Output('top-genres-chart', 'figure'),
            Output('top-labels-chart', 'figure'),
            Output('track-popularity-chart', 'figure'),
            Output('track-list', 'children')
        ],
        [Input('update-button', 'n_clicks')],
        [State('playlist-id-input', 'value')]
    )
    def update_dashboard(n_clicks, playlist_id):
        if not playlist_id:
            return ['', go.Figure(), go.Figure(), go.Figure(), go.Figure(), []]

        result = get_playlist_info(playlist_id)

        if not result:
            return ['Playlist not found', go.Figure(), go.Figure(), go.Figure(), go.Figure(), []]

        # Playlist Information
        playlist_info = [
            html.H6('Name: ' + result['name']),
            html.P('Description: ' + result['description']),
            html.P('Followers: ' + str(result['followers'])),
            html.P('Owner: ' + result['owner']),
            html.Img(src=result['image'], style={'width': '100%', 'margin-bottom': '20px'}),
            html.A('Open in Spotify', href=result['url'], target='_blank', className='btn btn-primary')
        ]

        # Top Artists Chart
        artists = result['stats']['artists_sorted_by_appearance'][:10]
        fig_artists = go.Figure(data=[go.Bar(
            x=[artist[0] for artist in artists],
            y=[artist[1] for artist in artists],
            text=[artist[1] for artist in artists],
            textposition='auto',
            marker_color='dodgerblue'
        )])
        fig_artists.update_layout(title='Top 10 Artists', xaxis_title='Artists', yaxis_title='Count')

        # Top Genres Chart
        genres = result['stats']['genres_sorted_by_appearance'][:10]
        fig_genres = go.Figure(data=[go.Bar(
            x=[genre[0] for genre in genres],
            y=[genre[1] for genre in genres],
            text=[genre[1] for genre in genres],
            textposition='auto',
            marker_color='darkorange'
        )])
        fig_genres.update_layout(title='Top 10 Genres', xaxis_title='Genres', yaxis_title='Count')

        # Top Labels Chart
        labels = result['stats']['labels_sorted_by_appearance'][:10]
        fig_labels = go.Figure(data=[go.Bar(
            x=[label[0] for label in labels],
            y=[label[1] for label in labels],
            text=[genre[1] for genre in genres],
            textposition='auto',
            marker_color='darkorange'
        )])
        fig_genres.update_layout(title='Top 10 Genres', xaxis_title='Genres', yaxis_title='Count')

        # Top Labels Chart
        labels = result['stats']['labels_sorted_by_appearance'][:10]
        fig_labels = go.Figure(data=[go.Bar(
            x=[label[0] for label in labels],
            y=[label[1] for label in labels],
            text=[label[1] for label in labels],
            textposition='auto',
            marker_color='darkgreen'
        )])
        fig_labels.update_layout(title='Top 10 Labels', xaxis_title='Labels', yaxis_title='Count')

        # Track Popularity Chart
        fig_popularity = go.Figure(data=[go.Histogram(
            x=[track['popularity'] for track in result['tracks']],
            nbinsx=20,
            marker_color='crimson'
        )])
        fig_popularity.update_layout(title='Track Distribution by Popularity', xaxis_title='Popularity',
                                     yaxis_title='Count')

        # Track List
        track_list = [
            dbc.Table([
                html.Thead(html.Tr([html.Th('Track Name'), html.Th('Artists'), html.Th('Label'), html.Th('Duration'),
                                    html.Th('Popularity')])),
                html.Tbody([
                    html.Tr([
                        html.Td(track['name']),
                        html.Td(track['artists']),
                        html.Td(track['label']),
                        html.Td(track['duration']),
                        html.Td(track['popularity'])
                    ]) for track in result['tracks']
                ])
            ], bordered=True, hover=True, responsive=True, striped=True)
        ]

        return [playlist_info, fig_artists, fig_genres, fig_labels, fig_popularity, track_list]

    return app
