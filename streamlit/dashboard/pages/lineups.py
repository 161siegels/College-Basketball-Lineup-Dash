from datetime import date
from typing import *

import pandas as pd
import streamlit as st
import numpy as np

from settings.helpers import GLOSSARY, summary_table
from dashboard.pages.base import BasePage, df_to_csv, download_button
import itertools

from data.data_loading import load_pbp_parquet, load_season_options, load_db_query, load_teams
from st_aggrid import AgGrid
from st_aggrid.grid_options_builder import GridOptionsBuilder
from st_aggrid.shared import JsCode, ColumnsAutoSizeMode

def ag_grid_cond_formatter(flipped: bool = False):
    if flipped:
        cellstyle_jscode = JsCode("""
            function(params){
                if (params.value == '0') {
                    return {
                        'color': 'black', 
                        'backgroundColor': 'orange',
                    }
                }
                if (params.value < '0') {
                    return{
                        'color': 'white',
                        'backgroundColor': 'green',
                    }
                }
                if (params.value > '0') {
                    return{
                        'color': 'white',
                        'backgroundColor': 'red',
                    }
                }
            }
            """)
    else:
        cellstyle_jscode = JsCode("""
        function(params){
            if (params.value == '0') {
                return {
                    'color': 'black', 
                    'backgroundColor': 'orange',
                }
            }
            if (params.value < '0') {
                return{
                    'color': 'white',
                    'backgroundColor': 'red',
                }
            }
            if (params.value > '0') {
                return{
                    'color': 'white',
                    'backgroundColor': 'green',
                }
            }
        }
        """)
    return cellstyle_jscode


@st.cache(ttl=60 * 60 * 24 * 5)
def load_players() -> pd.DataFrame:
    """Return a dataframe of the pbp"""
    df = load_db_query(f"""SELECT P.*, T.TeamName 
                       FROM CBB.Proc_Players P 
                       INNER JOIN
                       CBB.Proc_Teams T
                       ON P.NCAATeamId=T.NCAATeamId""")
    df['Player'] = df['NCAAPlayerCleanName'].astype(str)
    df['PlayerUnique'] = df['NCAAPlayerCleanName'].astype(str) + ' (' + df['TeamName'].astype(str) + ')'
    return df

class LineupsPage(BasePage):
    def __init__(self):
        super().__init__()
        self.pbp: Optional[pd.DataFrame] = None
        self.players: Optional[pd.DataFrame] = None
        self.teams: Optional[pd.DataFrame] = None
        self.team: str = None
        self.opp_team: Optional[List[str]] = None
        self.team_players_off: Optional[List[str]] = None
        self.team_players_on: Optional[List[str]] = None
        self.opp_team_players_off: Optional[List[str]] = None
        self.opp_team_players_on: Optional[List[str]] = None
        self.dates: Optional[Tuple[date]] = None
        self.query_dict: Optional[Dict] = {}
        self.chart_df: Optional[pd.DataFrame] = None
        self.season: Optional[str] = None
        self.team_player_vals : Optional[List[int]] = None
        self.opp_team_player_vals : Optional[List[int]] = None
        self.min_poss: Optional[int] = None
        self.lineup_df: pd.DataFrame = pd.DataFrame()

    def run(self):
        st.title('Lineup Combinations')
        self.season = st.sidebar.radio(
            label='Select a Season:',
            options=load_season_options()
        )
        # loading
        self.pbp = load_pbp_parquet(season=self.season)
        self.players = load_players()
        self.teams = load_teams()
        # st.header('Time Series Projections')
        # st.caption('''Names can be searched by typing. Hover over plot points for additional details.
        #         Streamlit has a dataframe size limit of 50MB.''')
        team, team_players_on, team_players_off, opp_team, opp_team_players_on, opp_team_players_off, = st.columns(
            6)
        with team:
            team_vals = self.filter_teams()
            self.team = st.selectbox(
                label='Team (ID):',
                options=team_vals,
                index=int(np.where(team_vals == 'Stanford (285)')[0][0])
            )
            self.query_dict['team'] = self.teams[self.teams['Team'] == self.team]['NCAATeamId'].unique()
            self.team_player_vals = self.filter_players(team_num='team')
        with team_players_on:
            self.team_players_on = st.multiselect(
                label='Team Players On (Team Name):',
                options=self.team_player_vals,
                default=None
            )
            self.query_dict['team_players_on'] = self.players[self.players['PlayerUnique'].isin(self.team_players_on)][
                'ESPN_PlayerId'].unique()
        with team_players_off:
            self.team_players_off = st.multiselect(
                label='Team Players off (Team Name):',
                options=self.team_player_vals,
                default=None
            )
            self.query_dict['team_players_off'] = \
            self.players[self.players['PlayerUnique'].isin(self.team_players_off)][
                'ESPN_PlayerId'].unique()

        with opp_team:
            team_vals = self.filter_teams()
            self.opp_team = st.multiselect(
                label='Opp Team (ID):',
                options=team_vals,
            )
            self.query_dict['opp_team'] = self.teams[self.teams['Team'].isin(self.opp_team)]['NCAATeamId'].unique()
            self.opp_team_player_vals = self.filter_players(team_num='opp_team')
        with opp_team_players_on:
            self.opp_team_players_on = st.multiselect(
                label='Opp Players On (Team Name):',
                options=self.opp_team_player_vals,
                default=None
            )
            self.query_dict['opp_team_players_on'] = \
            self.players[self.players['PlayerUnique'].isin(self.opp_team_players_on)][
                'ESPN_PlayerId'].unique()
        with opp_team_players_off:
            self.opp_team_players_off = st.multiselect(
                label='Opp Players Off (Team Name):',
                options=self.opp_team_player_vals,
                default=None
            )
            self.query_dict['opp_team_players_off'] = \
            self.players[self.players['PlayerUnique'].isin(self.opp_team_players_off)][
                'ESPN_PlayerId'].unique()

        min_poss, lineup_size, gd_col = st.columns([1, 1, 2])
        with min_poss:
            self.min_poss = st.number_input(
                label='Min Poss Played Together:',
                min_value=0,
                max_value=1000,
                step=1,
                value=50
            )
        with lineup_size:
            self.lineup_size = int(st.number_input(
                label='Lineup Size to evaluate:',
                min_value=1,
                max_value=5,
                step=1,
                value=1
            ))
        with gd_col:
            min_date = self.pbp['Date'].min()
            max_date = self.pbp['Date'].max()
            self.dates = st.slider(
                    label='Game Date Range:',
                    min_value=min_date,
                    max_value=max_date,
                    value=(min_date, max_date)
                )

        filtered_pbp = self.filter_pbp(df=self.pbp)
        self.lineup_df = self.get_lineup_combos(df=filtered_pbp, team_id=self.query_dict['team'], lineup_size=self.lineup_size)
        self.lineup_df = self.lineup_df.loc[lambda x: x['Poss_Count'].astype(int)>=self.min_poss]
        diff_cols = [c for c in self.lineup_df.columns if 'Diff_' in c]
        st.subheader("Differential Between Team and Opponents:")
        self.build_grid(self.lineup_df[["Poss_Count"]+diff_cols].reset_index(), cond_format=True)
        download_button(
        csv=df_to_csv(self.lineup_df[diff_cols].reset_index()),
        file_name=f'{self.team[0]} {self.lineup_size}_Man_Lineup'
        )
        st.subheader("All Data:")
        self.build_grid(self.lineup_df.reset_index(), cond_format=False)
        download_button(
        csv=df_to_csv(self.lineup_df.reset_index()),
        file_name=f'{self.team[0]} {self.lineup_size}_Man_Lineup'
        )
        st.write(GLOSSARY)

    def build_grid(self, df: pd.DataFrame, cond_format: bool):
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_first_column_as_index(resizable=True)
        gb.configure_columns(column_names=df.columns,
                             type=["numericColumn", "numberColumnFilter", "customNumericFormat"],
                             precision=2)
        gb.configure_columns(column_names=df.columns,
                             type=["numericColumn", "numberColumnFilter", "customNumericFormat"],
                             precision=2)
        gb.configure_columns(column_names=[c for c in df.columns if "%" in c],
                             type=["numericColumn", "numberColumnFilter", "customNumericFormat"],
                             precision=0,
                             valueFormatter="(Math.round(100*x)/100).toLocaleString() + '%'")
        if cond_format:
            gb.configure_columns(column_names=[c for c in df.columns if "Diff_" in c], cellStyle=ag_grid_cond_formatter())
            gb.configure_columns(column_names=["Diff_Poss_Length", "DiffTovPer100Poss"], cellStyle=ag_grid_cond_formatter(flipped=True))
        AgGrid(df, update_mode="VALUE_CHANGED", gridOptions=gb.build(), allow_unsafe_jscode=True,
               columns_auto_size_mode=ColumnsAutoSizeMode.FIT_CONTENTS)

    def filter_players(self, team_num: str) -> pd.DataFrame:
        player_df = self.players.loc[self.players['Season'] == self.season]
        if len(self.query_dict[team_num]) > 0:
            player_df = player_df.loc[player_df['NCAATeamId'].isin(self.query_dict[team_num])]
        return player_df["PlayerUnique"].unique()

    def filter_teams(self) -> pd.DataFrame:
        team_df = self.teams.loc[self.teams['Season'] == self.season]
        return team_df["Team"].unique()
    
    def filter_pbp(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return a filtered dataframe for plotting purposes"""
        filtered_df = df
        off_cols = [f"OffPlayer{i}Id" for i in range(1, 6)]
        def_cols = [f"DefPlayer{i}Id" for i in range(1, 6)]
        if len(self.query_dict['team']) > 0:
            filtered_df = filtered_df.loc[lambda x: (x['NCAAHomeTeamId'].isin(self.query_dict['team'])) |
                                            (x['NCAAAwayTeamId'].isin(self.query_dict['team']))]
        if len(self.query_dict['opp_team']) > 0:
            filtered_df = filtered_df.loc[lambda x: (x['NCAAHomeTeamId'].isin(self.query_dict['opp_team'])) |
                                            (x['NCAAAwayTeamId'].isin(self.query_dict['opp_team']))]
        if len(self.query_dict['team_players_on']) > 0:
            filtered_df = filtered_df.loc[filtered_df[off_cols+def_cols].isin(self.query_dict['team_players_on']).sum(axis=1) == len(
                self.query_dict['team_players_on'])]
        if len(self.query_dict['team_players_off']) > 0:
            filtered_df = filtered_df.loc[filtered_df[off_cols+def_cols].isin(self.query_dict['team_players_off']).sum(axis=1) == 0]
        if len(self.query_dict['opp_team_players_on']) > 0:
            filtered_df = filtered_df.loc[filtered_df[off_cols+def_cols].isin(self.query_dict['opp_team_players_on']).sum(axis=1) == len(
                self.query_dict['opp_team_players_on'])]
        if len(self.query_dict['opp_team_players_off']) > 0:
            filtered_df = filtered_df.loc[filtered_df[off_cols+def_cols].isin(self.query_dict['opp_team_players_off']).sum(axis=1) == 0]

        filtered_df = filtered_df.loc[lambda x: x['Date'].between(self.dates[0], self.dates[1])]
        return filtered_df

    @st.cache(ttl=60 * 60 * 24 * 5)
    def get_lineup_combos(self, df, team_id, lineup_size):
        if len(self.query_dict['team'])==0:
            return None
        players = self.players.loc[self.players['NCAATeamId'].isin(self.query_dict['team'])]
        combos = list(itertools.combinations(players['ESPN_PlayerId'].unique(), lineup_size))
        off_cols = [f"OffPlayer{i}Id" for i in range(1, 6)]
        def_cols = [f"DefPlayer{i}Id" for i in range(1, 6)]
        combo_dict = {}
        df_list = []
        for c in combos:
            combo_dict[c] = (df[off_cols + def_cols].isin(list(c)).sum(axis=1) == lineup_size)
            if combo_dict[c].sum() == 0:
                continue
            lineup_df = summary_table(df[combo_dict[c]], team_one=team_id,
                               team_two=[], team_df=self.teams)
            lineup_df = lineup_df.transpose()
            player_names = self.players.loc[self.players['ESPN_PlayerId'].isin(list(c))]['NCAAPlayerCleanName'].unique()
            lineup_df = pd.concat([lineup_df[:1].reset_index(drop=True),
                                   lineup_df[1:2].add_prefix('Opp_').reset_index(drop=True)], axis=1).rename(
                index={0: player_names})
            df_list.append(lineup_df)
        lineup_df = pd.concat(df_list, axis=0)
        for col in [c for c in lineup_df.columns if ("Opp_" not in c) and ("Man_Lineup" not in c)]:
            lineup_df[f"Diff_{col}"] = lineup_df[col] - lineup_df[f"Opp_{col}"]
        # lineup_df["PtsDiffPer100"] = lineup_df["PtsPer100Poss"] - lineup_df["Opp_PtsPer100Poss"]
        # col = lineup_df.pop("PtsDiffPer100")
        # lineup_df.insert(3, "PtsDiffPer100", col)
        lineup_df.sort_values("Poss_Count", ascending=False, inplace=True)
        lineup_df.index = lineup_df.index.map(str)
        return lineup_df.rename_axis(f"{lineup_size}_Man_Lineup")


