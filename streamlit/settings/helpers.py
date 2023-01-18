import pandas as pd

import streamlit as st
from pandas.api.types import (
    is_categorical_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
)
from typing import *
import numpy as np

POWER_6 = ["Big East", "ACC", "Pac-12", "SEC", "Big 12","Big Ten"]
GLOSSARY = f""" GLOSSARY:
            \nPoss_Count: Number of Possessions
            \nPoss_Length: Number of Seconds of Avg Poss
            \n% Transition: Percentage of Poss in transition
            \nPtsPer100Poss: Pts Per 100 Possessions
            \nTS%: True Shooting Percentage (Pts / (2 * (FG2A + FG3A + 0.44 * FTA))
            \nEFG%: Effective FG Percentage (FGM + 0.5 * 3PM) / FGA
            \nFTR: Free Throw Rate (FTA / FGA)
            \nFT%: Free Throw Percentage
            \nFG3AR: 3 Point Attempt Rate (FG3A / FGA)
            \nFG3%: 3 Point Percentage
            \nRimAR: Rim Attempt Rate ((Dunks+Layups) / FGA)
            \nRimFG%: FG% on Dunks and Layups
            \nAst%: Assist Percentage (Ast / (FGM))
            \nAst/Tov: Assist to Turnover Ratio
            \nTovPer100Poss: Turnovers Per 100 Possessions
            \nOreb%: Offensive Rebound Percentage (Oreb / (Oreb Opportunites))
            \nDreb%: Defensive Rebound Percentage (Dreb / (Dreb Opportunites))
            \nBlk%: Block Percentage (Blk / (Blk Opportunities)
            \nStlPer100Poss: Stl Per 100 Possessions"""

def filter_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds a UI on top of a dataframe to let viewers filter columns

    Args:
        df (pd.DataFrame): Original dataframe

    Returns:
        pd.DataFrame: Filtered dataframe
    """
    modify = st.checkbox("Add filters")

    if not modify:
        return df

    df = df.copy()

    # Try to convert datetimes into a standard format (datetime, no timezone)
    for col in df.columns:
        if is_object_dtype(df[col]):
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass

        if is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)

    modification_container = st.container()

    with modification_container:
        to_filter_columns = st.multiselect("Filter dataframe on", df.columns)
        for column in to_filter_columns:
            left, right = st.columns((1, 20))
            # Treat columns with < 10 unique values as categorical
            if is_categorical_dtype(df[column]) or df[column].nunique() < 10:
                user_cat_input = right.multiselect(
                    f"Values for {column}",
                    df[column].unique(),
                    default=list(df[column].unique()),
                )
                df = df[df[column].isin(user_cat_input)]
            elif is_numeric_dtype(df[column]):
                _min = float(df[column].min())
                _max = float(df[column].max())
                step = (_max - _min) / 100
                user_num_input = right.slider(
                    f"Values for {column}",
                    min_value=_min,
                    max_value=_max,
                    value=(_min, _max),
                    step=step,
                )
                df = df[df[column].between(*user_num_input)]
            elif is_datetime64_any_dtype(df[column]):
                user_date_input = right.date_input(
                    f"Values for {column}",
                    value=(
                        df[column].min(),
                        df[column].max(),
                    ),
                )
                if len(user_date_input) == 2:
                    user_date_input = tuple(map(pd.to_datetime, user_date_input))
                    start_date, end_date = user_date_input
                    df = df.loc[df[column].between(start_date, end_date)]
            else:
                user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                )
                if user_text_input:
                    df = df[df[column].astype(str).str.contains(user_text_input)]

    return df

def get_off_dict(data: pd.DataFrame):
    # self.teams[self.teams['Team'].isin(team_one)]
    # poss count
    poss_count = np.sum(data.groupby(["GameId", "PossNum"])["Event_Length"].sum() > 0)
    # poss length
    poss_length = np.sum(data.groupby(["GameId", "PossNum"])["Event_Length"].sum())
    # transition poss
    trans_poss = np.sum(data.groupby(["GameId", "PossNum"])["Transition"].mean() > 0)
    # pts
    pts = np.where(data['NCAAOffTeamId'] == data["NCAAHomeTeamId"],
                   data[f"HomeMarginalPoints"], data[f"AwayMarginalPoints"]).sum()
    # fg2a
    fg2a = np.sum(data['FGA']) - np.sum(data["EventType"] == "Three Point Jumper")
    fg3a = np.sum(data["EventType"] == "Three Point Jumper")
    fg2m = np.sum((data["EventType"] != "Three Point Jumper") & (data["EventResult"] == "made") & (data["FGA"] == 1))
    fg3m = np.sum((data["EventType"] == "Three Point Jumper") & (data["EventResult"] == "made") & (data["FGA"] == 1))
    fta = np.sum(data['FTA'])
    ftm = np.sum((data['FTA'] == 1) & (data["EventResult"] == "made"))
    layup_dunk_att = np.sum(data["EventType"] == "Layup") + np.sum(data["EventType"] == "Dunk")
    layup_dunk_m = np.sum(((data["EventType"] == "Layup") | (data["EventType"] == "Dunk")) & (
                data["EventResult"] == "made"))
    assist = np.sum(data["EventDescription"].str.contains(', assist'))
    # turnovers
    turnovers = np.sum(data["EventType"] == "Turnover")
    # off reb
    off_rebs = np.sum(data["EventType"] == "Offensive Rebound")
    pot_off_rebs = np.sum(data["EventType"] == "Offensive Rebound") + np.sum(data["EventType"] == "Defensive Rebound")
    off_summary = {
        'Poss_Count': poss_count,
        'Poss_Length': poss_length / poss_count,
        '%Transition': 100 * trans_poss / poss_count,
        'PtsPer100Poss': 100 * pts / poss_count,
        'TS%': 100*pts/(2*(fg2a+fg3a+0.44*fta)),
        'EFG%': (100*(fg3m*1.5+fg2m))/(fg2a+fg3a),
        "FTR": 100 * fta / (fg2a + fg3a),
        "FT%": 100 * ftm / fta,
        "FG3AR": 100 * fg3a / (fg2a + fg3a),
        "FG3%": 100 * fg3m / fg3a,
        "RimAR": 100 * layup_dunk_att / (fg2a + fg3a),
        "RimFG%": 100 * layup_dunk_m / layup_dunk_att,
        "Ast%": 100* assist / (fg3m + fg2m),
        "Ast/Tov": assist / turnovers,
        "TovPer100Poss": 100 * turnovers / poss_count,
        "Oreb%": 100 * off_rebs / pot_off_rebs,
    }

    def_rebs = np.sum(data["EventType"] == "Defensive Rebound")
    blks = np.sum(data["EventType"] == "Blocked Shot")
    stls = np.sum(data["EventType"] == "Steal")
    opp_dreb_opportunities = pot_off_rebs
    def_summary = {
        "Dreb%": def_rebs,
        "Blk%": 100 * blks / (fg2a),
        "StlPer100Poss": 100 * stls / poss_count,
    }
    return (off_summary, def_summary, opp_dreb_opportunities)

@st.cache(ttl=60 * 60 * 24 * 5)
def summary_table(data, team_one: List[str], team_two: List[str], team_df: pd.DataFrame):
    if len(data)==0:
        return pd.DataFrame()
    tm_name_one, tm_name_two = (None, None)
    if len(team_one)>0:
        team_1_data = data.loc[data.NCAAOffTeamId.isin(team_one)]
        tm_name_one = team_df.loc[team_df["NCAATeamId"].isin(team_one)]['TeamName']
        tm_name_one = (None if len(tm_name_one)>1 else tm_name_one.iloc[0])
    elif (len(team_one)==0) & (len(team_two)>0):
        team_1_data = data.loc[~data.NCAAOffTeamId.isin(team_two)]
    else:
        team_1_data = data
    if len(team_two)>0:
        team_2_data = data.loc[data.NCAAOffTeamId.isin(team_two)]
        tm_name_two = team_df.loc[team_df["NCAATeamId"].isin(team_two)]['TeamName']
        tm_name_two = (None if len(tm_name_two) > 1 else tm_name_two.iloc[0])
    elif (len(team_two)==0) & len(team_one)>0:
        team_2_data = data.loc[~data.NCAAOffTeamId.isin(team_one)]
    else:
        team_2_data = data

    # post hoc divide Dreb sum by dreb opportunities
    (off_summary_1, def_summary_2, dreb_opportunities_1) = get_off_dict(team_1_data)
    (off_summary_2, def_summary_1, dreb_opportunities_2) = get_off_dict(team_2_data)
    def_summary_1['Dreb%'] = 100 - off_summary_2['Oreb%']
    def_summary_2['Dreb%'] = 100 - off_summary_1['Oreb%']
    # def_summary_1['Dreb%'] = 100*def_summary_1['Dreb%']/dreb_opportunities_1
    # def_summary_2['Dreb%'] = 100 * def_summary_2['Dreb%'] / dreb_opportunities_2
    # def_summary_1 = {k: str(v) for k, v in def_summary_1.items()}
    # def_summary_2 = {k: str(v) for k, v in def_summary_2.items()}

    tm_one_df = pd.DataFrame.from_dict({**off_summary_1, **def_summary_1}, orient="index",
                           columns=[f"{tm_name_one}" if tm_name_one else "Team 1"])
    tm_two_df = pd.DataFrame.from_dict({**off_summary_2, **def_summary_2}, orient="index",
                           columns=[f"{tm_name_two}" if tm_name_two else "Team 2"])
    combined_df = pd.concat([tm_one_df, tm_two_df], axis=1)
    combined_df["Differential"] = combined_df.iloc[:, 0] - combined_df.iloc[:, 1]
    return combined_df

@st.cache(ttl=60 * 60 * 24 * 5)
def power_6_pbp(pbp, power_6_teams):
    power_6_ids = power_6_teams['NCAATeamId'].unique()
    pbp_filtered = pbp.loc[(pbp['NCAAHomeTeamId'].isin(power_6_ids)) & (pbp['NCAAAwayTeamId'].isin(power_6_ids))]
    return pbp_filtered