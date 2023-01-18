from datetime import date, timedelta
from typing import *

import pandas as pd
import streamlit as st

from settings.helpers import POWER_6, GLOSSARY, summary_table, power_6_pbp
from dashboard.pages.base import BasePage, df_to_csv, download_button
from data.data_loading import load_games, load_teams, load_players, load_pbp_parquet, load_season_options

from plotting.plotting_helpers import bokeh_shot_chart




class ShotChartPage(BasePage):
    def __init__(self):
        super().__init__()
        self.pbp: Optional[pd.DataFrame] = None
        self.team_one_players_on: Optional[List[str]] = None
        self.team_one_players_off: Optional[List[str]] = None
        self.team_two_players_on: Optional[List[str]] = None
        self.team_two_players_off: Optional[List[str]] = None
        self.team_one: Optional[List[str]] = None
        self.team_two: Optional[List[str]] = None
        self.dates: Optional[Tuple[date]] = None
        self.query_dict: Optional[Dict] = {}
        self.plot_teams: Optional[List[int]] = []
        self.plot_df: Optional[pd.DataFrame] = None
        self.chart_df: Optional[pd.DataFrame] = None
        self.season: Optional[str] = None
        self.plot_color : Tuple[str, str] =  None
        self.team_one_color: str = None
        self.team_two_color: str = None
        self.power_6_teams_two: bool = False
        self.conference_teams_two: bool = False

        self.plot_team_options : Optional[List[str]] = None
        self.team_one_player_vals : Optional[List[int]] = None
        self.team_two_player_vals : Optional[List[int]] = None
        self.players: pd.DataFrame = None
        self.teams: pd.DataFrame = None
        self.games: pd.DataFrame = None

    def run(self):
        st.title('Shot Chart')
        self.season = st.sidebar.radio(
            label='Select a Season:',
            options=load_season_options()
        )
        # loading
        self.pbp = load_pbp_parquet(season=self.season)
        self.players = load_players()
        self.teams = load_teams()
        self.games = load_games()

        # st.header('Time Series Projections')
        # st.caption('''Names can be searched by typing. Hover over plot points for additional details.
        # Streamlit has a dataframe size limit of 50MB.''')
        team_one, team_one_players_on, team_one_players_off, team_two, team_two_players_on, team_two_players_off, = st.columns(6)
        with team_one:
            team_vals = self.filter_teams()
            self.team_one = st.multiselect(
                label='Team 1 (ID):',
                options=team_vals,
                default='Stanford (285)'
            )
            self.query_dict['team_one'] = self.teams[self.teams['Team'].isin(self.team_one)]['NCAATeamId'].unique()
            self.team_one_player_vals = self.filter_players(team_num='team_one')
            self.plot_team_options = [t for t in ((self.team_one if self.team_one else [])+(self.team_two if self.team_two else []))]
            if self.team_one:
                self.team_one_color = self.teams[self.teams['Team'].isin(self.team_one)]['PrimaryColor'].iloc[0]
            else:
                self.team_one_color = "white"
        with team_one_players_on:
            self.team_one_players_on = st.multiselect(
                label='Team 1 Players On (ID):',
                options=self.team_one_player_vals,
                default=None
            )
            self.query_dict['team_one_players_on'] = self.players[self.players['Player'].isin(self.team_one_players_on)][
                'ESPN_PlayerId'].unique()
        with team_one_players_off:
            self.team_one_players_off = st.multiselect(
                label='Team 1 Players off (ID):',
                options=self.team_one_player_vals,
                default=None
            )
            self.query_dict['team_one_players_off'] = self.players[self.players['Player'].isin(self.team_one_players_off)][
                'ESPN_PlayerId'].unique()



        team_one_filters, empty_col, team_two_filters, empty_col_2 = st.columns([1, 2, 1, 2])

        with team_two_filters:
            self.power_6_teams_two = st.checkbox('Power 6 teams')
            self.conference_teams_two = st.checkbox('Conference Opponents')
            if self.power_6_teams_two:
                self.team_two = self.get_power_6_teams()['Team'].unique()
                self.team_two = [t for t in self.team_two if t not in self.team_one]
                self.query_dict['team_two'] = self.teams[self.teams['Team'].isin(self.team_two)]['NCAATeamId'].unique()
                self.team_two_player_vals = self.filter_players(team_num='team_two')
            if self.conference_teams_two:
                tm_one_conf = self.get_tm_conference(team=self.team_one)
                self.team_two = self.teams[lambda x: x['Conference'].isin(tm_one_conf)]['Team'].unique()
                self.team_two = [t for t in self.team_two if t not in self.team_one]
                self.query_dict['team_two'] = self.teams[self.teams['Team'].isin(self.team_two)]['NCAATeamId'].unique()
                self.team_two_player_vals = self.filter_players(team_num='team_two')

        with team_two:
            team_vals = self.filter_teams()
            if self.power_6_teams_two or self.conference_teams_two:
                st.session_state.team_two=[]
                self.team_two_color = "white"
            else:
                self.team_two = st.multiselect(
                    label='Team 2 Team (ID):',
                    options=team_vals,
                    key='team_two'
                )
                self.query_dict['team_two'] = self.teams[self.teams['Team'].isin(self.team_two)]['NCAATeamId'].unique()
                self.team_two_player_vals = self.filter_players(team_num='team_two')
                self.plot_team_options = [t for t in ((self.team_one if self.team_one else [])+(self.team_two if self.team_two else []))]
                if self.team_two:
                    self.team_two_color = self.teams[self.teams['Team'].isin(self.team_two)]['PrimaryColor'].iloc[0]
                else:
                    self.team_two_color = "white"
        with team_two_players_on:
            if self.power_6_teams_two or self.conference_teams_two:
                st.session_state.team_two_players_on=[]
                self.query_dict['team_two_players_on'] = []
            else:
                self.team_two_players_on = st.multiselect(
                    label='Team 2 Players On (ID):',
                    options=self.team_two_player_vals,
                    default=None,
                    key='team_two_players_on'
                )
                self.query_dict['team_two_players_on'] = self.players[self.players['Player'].isin(self.team_two_players_on)][
                    'ESPN_PlayerId'].unique()
        with team_two_players_off:
            if self.power_6_teams_two or self.conference_teams_two:
                st.session_state.team_two_players_off=[]
                self.query_dict['team_two_players_off'] = []
            else:
                self.team_two_players_off = st.multiselect(
                    label='Team 2 Players Off (ID):',
                    options=self.team_two_player_vals,
                    key='team_two_players_off',
                    default=None
                )
                self.query_dict['team_two_players_off'] = self.players[self.players['Player'].isin(self.team_two_players_off)][
                    'ESPN_PlayerId'].unique()

        min_date = self.pbp['Date'].min()
        max_date = self.pbp['Date'].max()
        plot_specify_col, gd_col = st.columns([1, 3])
        with plot_specify_col:
            self.plot_teams = st.multiselect(
                label='Plot Team Shot Chart:',
                options=self.plot_team_options + (["Opponent"] if len(self.plot_team_options)==1 else [])
            )
            if self.plot_teams:
                if self.plot_teams == ["Opponent"]:
                    self.plot_color = ("blue", "black")
                else:
                    self.plot_color = (self.teams[self.teams['Team'].isin(self.plot_teams)]['PrimaryColor'].iloc[0],
                                       self.teams[self.teams['Team'].isin(self.plot_teams)]['SecondaryColor'].iloc[0])
            elif self.team_one:
                self.plot_color = (self.teams[self.teams['Team'].isin(self.team_one)]['PrimaryColor'].iloc[0],
                                   self.teams[self.teams['Team'].isin(self.team_one)]['SecondaryColor'].iloc[0])
            elif self.team_two:
                self.plot_color = (self.teams[self.teams['Team'].isin(self.team_two)]['PrimaryColor'].iloc[0],
                                   self.teams[self.teams['Team'].isin(self.team_two)]['SecondaryColor'].iloc[0])
            else:
                self.plot_color = ("blue", "black")
            if self.plot_teams == ["Opponent"]:
                self.query_dict['plot_teams'] = self.teams[~self.teams['Team'].isin(self.plot_team_options)][
                    'NCAATeamId'].unique()
            else:
                self.query_dict['plot_teams'] = self.teams[self.teams['Team'].isin(self.plot_teams)]['NCAATeamId'].unique()
        with gd_col:
            self.dates = st.slider(
                label='Game Date Range:',
                min_value=min_date,
                max_value=max_date,
                value=(min_date, max_date)
            )
        self.plot_df = self.filter_plot_df(self.pbp, plot=True)
        self.chart_df = self.filter_plot_df(self.pbp, plot=False)
        # st.pyplot(shot_chart(data=self.plot_df, color=self.plot_color))
        col_5, col_6 = st.columns([2, 2])
        with col_5:
            if self.team_one or self.team_two:
                st.bokeh_chart(bokeh_shot_chart(data=self.plot_df, fill_color=self.plot_color[0]))
                st.subheader("Games with shot location:")
                shot_loc_games = self.plot_df.loc[~self.plot_df["ESPN_Shot_X"].isna()]
                st.table(self.games[self.games["GameId"].isin(shot_loc_games['GameId'])].set_index('GameId'),
                            )
        with col_6:
            if self.team_one or self.team_two:
                df= summary_table(self.chart_df, team_one=self.query_dict['team_one'],
                team_two=self.query_dict['team_two'], team_df = self.teams)
                power_6_df = summary_table(power_6_pbp(pbp=self.pbp, power_6_teams=self.get_power_6_teams()), team_one=[],
                              team_two=[], team_df = self.teams)
                df = pd.concat([df, power_6_df['Team 1'].rename('Avg Power 6 Team')], axis=1)
                self.display_df(df)
                download_button(
                csv=df_to_csv(df),
                file_name='pbp_rollups'
                )
                st.write(GLOSSARY)

    def plot_map(self) -> dict:
        """Return a mapping dictionary for the layered plots used with ZB/DARKO"""
        id_vars = ['PlayerId', 'Name', 'RunDate']
        plot_map = {
            'zb': {
                'df': self.plot_df,
                'ratings': self.zb_ratings,
                'id_vars': id_vars,
                'tooltip': id_vars + ['Value']
            },
            'darko': {
                'df': self.darko_plot_df,
                'ratings': self.darko_ratings,
                'id_vars': id_vars + ['tm_id', 'game_id'],
                'tooltip': id_vars + ['tm_id', 'game_id', 'Value']
            }
        }
        return plot_map

    def filter_plot_df(self, df: pd.DataFrame, plot: bool = False) -> pd.DataFrame:
        """Return a filtered dataframe for plotting purposes"""
        plot_df = df
        off_cols = [f"OffPlayer{i}Id" for i in range(1, 6)]
        def_cols = [f"DefPlayer{i}Id" for i in range(1, 6)]
        if len(self.query_dict['team_one']) > 0:
            plot_df = plot_df.loc[lambda x: (x['NCAAHomeTeamId'].isin(self.query_dict['team_one'])) |
                                            (x['NCAAAwayTeamId'].isin(self.query_dict['team_one']))]
        if len(self.query_dict['team_two']) > 0:
            plot_df = plot_df.loc[lambda x: (x['NCAAHomeTeamId'].isin(self.query_dict['team_two'])) |
                                            (x['NCAAAwayTeamId'].isin(self.query_dict['team_two']))]
        if len(self.query_dict['team_one_players_on']) > 0:
            plot_df = plot_df.loc[plot_df[off_cols+def_cols].isin(self.query_dict['team_one_players_on']).sum(axis=1) == len(
                self.query_dict['team_one_players_on'])]
        if len(self.query_dict['team_one_players_off']) > 0:
            plot_df = plot_df.loc[plot_df[off_cols+def_cols].isin(self.query_dict['team_one_players_off']).sum(axis=1) == 0]
        if len(self.query_dict['team_two_players_on']) > 0:
            plot_df = plot_df.loc[plot_df[off_cols+def_cols].isin(self.query_dict['team_two_players_on']).sum(axis=1) == len(
                self.query_dict['team_two_players_on'])]
        if len(self.query_dict['team_two_players_off']) > 0:
            plot_df = plot_df.loc[plot_df[off_cols+def_cols].isin(self.query_dict['team_two_players_off']).sum(axis=1) == 0]

        if plot & (len(self.query_dict['plot_teams'])>0):
            plot_df = plot_df.loc[lambda x: x['NCAAOffTeamId'].isin(self.query_dict['plot_teams'])]

        plot_df = plot_df.loc[lambda x: x['Date'].between(self.dates[0], self.dates[1])]
        return plot_df

    def filter_teams(self) -> pd.DataFrame:
        team_df = self.teams.loc[self.teams['Season'] == self.season]
        return team_df["Team"].unique()

    def filter_players(self, team_num: str) -> pd.DataFrame:
        player_df = self.players.loc[self.players['Season'] == self.season]
        if len(self.query_dict[team_num]) > 0:
            player_df = player_df.loc[player_df['NCAATeamId'].isin(self.query_dict[team_num])]
        return player_df["Player"].unique()

    def get_tm_conference(self, team: List[str]):
        if len(team) == 0:
            return self.teams['Conference'].unique()
        tm = self.teams.loc[lambda x: x["Team"].isin(team)]
        return tm['Conference'].unique()

    def get_power_6_teams(self):
        return self.teams[lambda x: x['Conference'].isin(POWER_6)].copy()

    def display_df(self, df):
        styles = [
            dict(selector="tr:hover",
                 props=[("background", "cyan"), ]),
            dict(selector="th", props=[("color", "black"),
                                       ("border", "1px solid"),
                                       ("padding", "12px 25px"),
                                       ('text-align', 'center'),
                                       ("border-collapse", "collapse"),
                                       ("background", "white"),
                                       ("font-size", "17px")
                                       ]),
            dict(selector="th:nth-child(3)", props=[
                ("background", self.team_two_color),
            ]),
            dict(selector="th:nth-child(2)", props=[
                ("color", "black"),
                ("border", "1px solid"),
                ("padding", "12px 35px"),
                ('text-align', 'center'),
                ("border-collapse", "collapse"),
                ("font-size", "18px"),
                ("background", self.team_one_color),
            ]),
            dict(selector="td", props=[("color", "black"),
                                       ("border", "1px solid #eee"),
                                       ("padding", "12px 35px"),
                                       ("border-collapse", "collapse"),
                                       ("font-size", "15px")
                                       ]),
            dict(selector="table", props=[
                ("font-family", 'Arial'),
                ("margin", "5px auto"),
                ("border-collapse", "collapse"),
                ("border", "1px solid #eee"),
                ("border-bottom", "2px solid #00cccc"),
            ])
        ]
        return st.table(df.style.highlight_max(color='lightblue', axis=1,
                                        subset=([c for c in df.columns if c != 'Avg Power 6 Team'])).
                 format("{:.2f}").background_gradient(
            axis=0,
            cmap='RdYlGn',
            subset=(df.index[1:len(df.index)], [c for c in df.columns if 'Differential' in c])
        ).set_table_styles(styles).set_properties(**{'text-align': 'center'}))

