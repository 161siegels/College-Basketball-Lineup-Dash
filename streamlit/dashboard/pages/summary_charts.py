from datetime import date, timedelta
from typing import *

import pandas as pd
import streamlit as st
import numpy as np

from dashboard.pages.base import BasePage, df_to_csv, download_button
from data.data_loading import load_pbp_parquet, load_season_options, load_db_table, load_teams
from settings.helpers import POWER_6, GLOSSARY, power_6_pbp

from settings.helpers import summary_table

@st.cache(ttl=60 * 60 * 24 * 5)
def load_players() -> pd.DataFrame:
    """Return a dataframe of the pbp"""
    df = load_db_table('CBB.Proc_Players')
    df['HeightInches'] = df['HeightInches'].fillna(df['HeightInches'].mean())
    feet = (df['HeightInches']/12).astype(int)
    inches = (df['HeightInches'].mod(12).astype(int))
    df['Player'] = df['NCAAPlayerCleanName'].astype(str) + ' (' + feet.astype(str) + "\'" + inches.astype(str) + ')'
    df['Player'] = df['Player'].astype(str)
    return df



class SummaryChartPage(BasePage):
    def __init__(self):
        super().__init__()
        self.pbp: Optional[pd.DataFrame] = None
        self.team: Optional[List[str]] = None
        self.team_two: Optional[List[str]] = None
        self.dates: Optional[Tuple[date]] = None
        self.season: Optional[str] = None
        self.power_6_teams_two: bool = False
        self.conference_teams_two: bool = False
        self.query_dict: Dict = {}

    def run(self):
        st.title('Team Summary Charts')
        self.season = st.sidebar.radio(
            label='Select a Season:',
            options=load_season_options()
        )
        # loading
        self.pbp = load_pbp_parquet(season=self.season)
        self.players = load_players()
        self.teams = load_teams()
        team_one, team_one_sm_big, team_one_players_on, team_one_players_off, team_two, team_two_filters = st.columns([1,1,1,1,1, 1])

        with team_one:
            team_vals = self.filter_teams()
            self.team = st.selectbox(
                label='Team (ID):',
                options=team_vals,
                index=int(np.where(team_vals == 'Stanford (285)')[0][0])
            )
            self.query_dict['team'] = self.teams[self.teams['Team'] == self.team]['NCAATeamId'].unique()
            self.team_name =  self.teams[self.teams['Team'] == self.team]['TeamName'].unique()
            self.team_player_vals = self.filter_players(team_num='team')

        with team_one_sm_big:
            self.team_one_sm_big = st.checkbox('Team 1: Small vs Big Analysis')
            if self.team_one_sm_big:
                self.max_height_one = st.number_input(
                    label='Max Height in Inches Small Lineup:',
                    min_value=0,
                    max_value=1000,
                    step=1,
                    value=81
                )
                big_players = self.players[(self.players['HeightInches'] > self.max_height_one) &
                                           (self.players['NCAATeamId'].isin(self.query_dict['team']))]

                self.query_dict['big_players'] = big_players['ESPN_PlayerId'].unique().tolist()
                feet = int(self.max_height_one / 12)
                inches = (self.max_height_one%12)
                height_str = str(feet) + "\'" + str(inches)
                st.write(f"Considering {height_str} and Shorter as small. Big Players: ")
                st.write(', '.join(map(str, big_players['Player'].unique().tolist())))
        with team_one_players_off:
            players_off = self.query_dict.get('team_players_off')
            default_vals = None
            if players_off is not None:
                default_vals = self.players[self.players['ESPN_PlayerId'].isin(self.query_dict['team_players_off'])]['Player'].unique()
                default_vals = default_vals[np.isin(default_vals, self.team_player_vals)]
            self.team_players_off = st.multiselect(
                label='Team 1 Players Off (Height):',
                options=self.team_player_vals,
                default=default_vals
            )
            self.query_dict['team_players_off'] = \
            self.players[self.players['Player'].isin(self.team_players_off)][
                'ESPN_PlayerId'].unique()
        with team_one_players_on:
            players_on = self.query_dict.get('team_players_on')
            default_vals = None
            if players_on is not None:
                default_vals = self.players[self.players['ESPN_PlayerId'].isin(self.query_dict['team_players_on'])]['Player'].unique()
                default_vals = default_vals[np.isin(default_vals, self.team_player_vals)]
            self.team_players_on = st.multiselect(
                label='Team 1 Players On (Height):',
                options=self.team_player_vals,
                default=default_vals
            )
            self.query_dict['team_players_on'] = \
            self.players[self.players['Player'].isin(self.team_players_on)][
                'ESPN_PlayerId'].unique()
        with team_two_filters:
            self.power_6_teams_two = st.checkbox('Power 6 teams')
            self.conference_teams_two = st.checkbox('Conference Opponents')
            if self.power_6_teams_two:
                self.team_two = self.get_power_6_teams()['Team'].unique()
                self.team_two = [t for t in self.team_two if t != self.team]
                self.query_dict['team_two'] = self.teams[self.teams['Team'].isin(self.team_two)]['NCAATeamId'].unique()
            if self.conference_teams_two:
                tm_one_conf = self.get_tm_conference(team=[self.team])
                self.team_two = self.teams[lambda x: x['Conference'].isin(tm_one_conf)]['Team'].unique()
                self.team_two = [t for t in self.team_two if t != self.team]
                self.query_dict['team_two'] = self.teams[self.teams['Team'].isin(self.team_two)]['NCAATeamId'].unique()
            # self.team_one_sm_big = st.checkbox('Team 1: Small vs Big Analysis')
            # if self.team_one_sm_big:
            #     self.max_height_one = st.number_input(
            #         label='Max Height in Inches Small Lineup:',
            #         min_value=0,
            #         max_value=1000,
            #         step=1,
            #         value=81
            #     )
            #     big_players = self.players[(self.players['HeightInches'] > self.max_height_one) &
            #                                (self.players['NCAATeamId'].isin(self.query_dict['team']))]
            #
            #     self.query_dict['big_players'] = big_players['ESPN_PlayerId'].unique().tolist()
            #     feet = int(self.max_height_one / 12)
            #     inches = (self.max_height_one % 12)
            #     height_str = str(feet) + "\'" + str(inches)
        # Team 2
        with team_two:
            team_vals = self.filter_teams()
            if self.power_6_teams_two or self.conference_teams_two:
                st.session_state.team_two = []
            else:
                self.team_two = st.multiselect(
                    label='Team 2 Team (ID):',
                    options=team_vals,
                    key='team_two'
                )
                self.query_dict['team_two'] = self.teams[self.teams['Team'].isin(self.team_two)]['NCAATeamId'].unique()



        self.dates = st.slider(
            label='Game Date Range:',
            min_value=self.pbp['Date'].min(),
            max_value=self.pbp['Date'].max(),
            value=(self.pbp['Date'].min(), self.pbp['Date'].max())
        )
        if len(self.team)==0:
            return
        if self.team_one_sm_big:
            # if this check, then run one df with the big guys off the court. Another with at least one on

            self.chart_df = self.filter_plot_df(self.pbp)
            for type in ["Small", "Big"]:
                if type == "Small":
                    small_df = self.filter_small_df(df=self.chart_df, big_players=self.query_dict['big_players'])
                    small_df = summary_table(small_df, team_one=self.query_dict['team'],
                                           team_two=[], team_df=self.teams)
                else:
                    big_df = self.filter_big_df(df=self.chart_df, big_players=self.query_dict['big_players'])
                    big_df = summary_table(big_df, team_one=self.query_dict['team'],
                                        team_two=[], team_df=self.teams)
            df = pd.concat([small_df.add_prefix('Small_'), big_df.add_prefix('Big_')], axis=1)
            df.columns = df.columns.str.replace('Team 2', f'{self.team_name[0]} Opponents')
            power_6_df = summary_table(power_6_pbp(pbp=self.pbp, power_6_teams=self.get_power_6_teams()), team_one=[],
                                       team_two=[], team_df=self.teams)
            df = pd.concat([df, power_6_df['Team 1'].rename('Avg Power 6 Team')], axis=1)
        else:
            self.chart_df = self.filter_plot_df(self.pbp)

            df = summary_table(self.chart_df, team_one=self.query_dict['team'],
                               team_two=[], team_df=self.teams)
            df.columns = df.columns.str.replace('Team 2', f'{self.team_name[0]} Opponents')
            power_6_df = summary_table(power_6_pbp(pbp=self.pbp, power_6_teams=self.get_power_6_teams()), team_one=[],
                                       team_two=[], team_df=self.teams)
            df = pd.concat([df, power_6_df['Team 1'].rename('Avg Power 6 Team')], axis=1)
            df["Diff w Avg Power 6 Team"] = df.iloc[:, 0] - df['Avg Power 6 Team']
        st.table(df.style.background_gradient(
                        axis=0,
                        cmap='RdYlGn',
                        subset = (df.index[1:len(df.index)], [c for c in df.columns if 'Diff' in c])
                    ).format("{:.2f}"))
        download_button(
            csv=df_to_csv(df),
            file_name='summary_chart'
        )
        st.write(
            GLOSSARY
        )

    def filter_plot_df(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a filtered dataframe for plotting purposes"""
        plot_df = df
        off_cols = [f"OffPlayer{i}Id" for i in range(1, 6)]
        def_cols = [f"DefPlayer{i}Id" for i in range(1, 6)]
        if len(self.query_dict['team']) > 0:
            plot_df = plot_df.loc[lambda x: (x['NCAAHomeTeamId'].isin(self.query_dict['team'])) |
                                            (x['NCAAAwayTeamId'].isin(self.query_dict['team']))]
        if len(self.query_dict['team_two']) > 0:
            plot_df = plot_df.loc[lambda x: (x['NCAAHomeTeamId'].isin(self.query_dict['team_two'])) |
                                            (x['NCAAAwayTeamId'].isin(self.query_dict['team_two']))]
        if len(self.query_dict['team_players_on']) > 0:
            plot_df = plot_df.loc[plot_df[off_cols+def_cols].isin(self.query_dict['team_players_on']).sum(axis=1) == len(
                self.query_dict['team_players_on'])]
        if len(self.query_dict['team_players_off']) > 0:
            plot_df = plot_df.loc[plot_df[off_cols+def_cols].isin(self.query_dict['team_players_off']).sum(axis=1) == 0]

        plot_df = plot_df.loc[lambda x: x['Date'].between(self.dates[0], self.dates[1])]
        return plot_df

    def filter_small_df(self, df: pd.DataFrame, big_players):
        plot_df = df
        off_cols = [f"OffPlayer{i}Id" for i in range(1, 6)]
        def_cols = [f"DefPlayer{i}Id" for i in range(1, 6)]
        if len(big_players) > 0:
            plot_df = plot_df.loc[plot_df[off_cols + def_cols].isin(big_players).sum(axis=1) == 0]
        return plot_df

    def filter_big_df(self, df: pd.DataFrame, big_players):
        plot_df = df
        off_cols = [f"OffPlayer{i}Id" for i in range(1, 6)]
        def_cols = [f"DefPlayer{i}Id" for i in range(1, 6)]
        if len(big_players) > 0:
            plot_df = plot_df.loc[plot_df[off_cols + def_cols].isin(big_players).sum(axis=1) > 0]
        return plot_df

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

    def filter_teams(self) -> pd.DataFrame:
        team_df = self.teams.loc[self.teams['Season'] == self.season]
        return team_df["Team"].unique()