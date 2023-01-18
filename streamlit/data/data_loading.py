import pandas as pd
import numpy as np
import streamlit as st

import sqlalchemy
import pathlib

def load_db_table(table):
    engine = sqlalchemy.create_engine('mysql://root:tarheels2020@localhost')
    conn = engine.connect()
    df = pd.read_sql(f"SELECT * FROM {table}", conn)
    conn.close()
    return df


def load_db_query(query):
    engine = sqlalchemy.create_engine('mysql://root:tarheels2020@localhost')
    conn = engine.connect()
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def read_csv(table):
    return pd.read_csv(f'{pathlib.Path().absolute()}/data/{table}.csv')

def read_parquet(file):
    return pd.read_parquet(f'{pathlib.Path().absolute()}/data/{file}.parquet')

@st.cache(ttl=60 * 60 * 24 * 5)
def load_pbp() -> pd.DataFrame:
    """Return a dataframe of the pbp"""
    df = load_db_query(f"""SELECT GameId, Date, Season, Home, Away, NCAAHomeTeamId, NCAAAwayTeamId, GameSeconds, HomeScore, AwayScore,
                            PossNum, EventDescription, EventType, EventResult, Event_Length, Transition, ShotValue, FGA,
                            FTA, NCAAEventTeamId, HomePlayer1Id, HomePlayer2Id, HomePlayer3Id, HomePlayer4Id,HomePlayer5Id,
                            AwayPlayer1Id, AwayPlayer2Id, AwayPlayer3Id, AwayPlayer4Id,AwayPlayer5Id, HomeMarginalPoints, 
                            AwayMarginalPoints, NCAAOffTeamId, NCAADefTeamId, ESPN_Shot_X, ESPN_Shot_Y FROM CBB.Proc_PBP;""")
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    for i in range(1, 6):
        df[f"OffPlayer{i}Id"] = np.where(df["NCAAOffTeamId"] == df["NCAAHomeTeamId"], df[f"HomePlayer{i}Id"], df[f"AwayPlayer{i}Id"])
        df[f"DefPlayer{i}Id"] = np.where(df["NCAAOffTeamId"] == df["NCAAHomeTeamId"], df[f"AwayPlayer{i}Id"], df[f"HomePlayer{i}Id"])
    df['ESPN_Shot_X'] = np.where(df['ESPN_Shot_Y'] > 47, 50 - df['ESPN_Shot_X'], df['ESPN_Shot_X'])-25
    df['ESPN_Shot_Y'] = np.where(df['ESPN_Shot_Y'] > 47, 94 - df['ESPN_Shot_Y'], df['ESPN_Shot_Y'])
    df["ShotDistance"] = np.sqrt(df["ESPN_Shot_X"]**2 + df["ESPN_Shot_Y"]**2)
    df["DateString"] = pd.to_datetime(df["Date"]).dt.date.astype(str)
    return df

@st.cache(ttl=60 * 60 * 24 * 5)
def load_pbp_parquet(season: str) -> pd.DataFrame:
    """Return a dataframe of the pbp"""
    df = read_parquet(f'pbp_sn_{season}')
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    for i in range(1, 6):
        df[f"OffPlayer{i}Id"] = np.where(df["NCAAOffTeamId"] == df["NCAAHomeTeamId"], df[f"HomePlayer{i}Id"], df[f"AwayPlayer{i}Id"])
        df[f"DefPlayer{i}Id"] = np.where(df["NCAAOffTeamId"] == df["NCAAHomeTeamId"], df[f"AwayPlayer{i}Id"], df[f"HomePlayer{i}Id"])
    df['ESPN_Shot_X'] = np.where(df['ESPN_Shot_Y'] > 47, 50 - df['ESPN_Shot_X'], df['ESPN_Shot_X'])-25
    df['ESPN_Shot_Y'] = np.where(df['ESPN_Shot_Y'] > 47, 94 - df['ESPN_Shot_Y'], df['ESPN_Shot_Y'])
    df["ShotDistance"] = np.sqrt(df["ESPN_Shot_X"]**2 + df["ESPN_Shot_Y"]**2)
    df["DateString"] = pd.to_datetime(df["Date"]).dt.date.astype(str)
    return df

@st.cache(ttl=60 * 60 * 24 * 5)
def load_season_options() -> pd.DataFrame:
    """Return a dataframe of the pbp"""
    df = load_db_query('SELECT DISTINCT Season FROM CBB.Proc_PBP')
    return df["Season"].unique()

@st.cache(ttl=60 * 60 * 24 * 5)
def load_players() -> pd.DataFrame:
    """Return a dataframe of the pbp"""
    df = load_db_table('CBB.Proc_Players')
    df['Player'] = df['NCAAPlayerCleanName'].astype(str) + ' (' + df['ESPN_PlayerId'].astype(str) + ')'
    df['Player'] = df['Player'].astype(str)
    return df


@st.cache(ttl=60 * 60 * 24 * 5)
def load_teams() -> pd.DataFrame:
    """Return a dataframe of the pbp"""
    df = load_db_table('CBB.Proc_Teams')
    df["Team"] = df['TeamName'].astype(str) + ' (' + df['TeamId'].astype(str) + ')'
    return df

@st.cache(ttl=60 * 60 * 24 * 5)
def load_games() -> pd.DataFrame:
    """Return a dataframe of the pbp"""
    df = load_db_table('CBB.Proc_Schedule')
    df["Date"] = pd.to_datetime(df["Date"]).dt.date
    df = df[["GameId", "Date", "isNeutral", "HomeTeamName", "AwayTeamName", "HomeTeamScore", "AwayTeamScore"]]
    return df