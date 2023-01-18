import datetime
from typing import *

import pandas as pd
import streamlit as st
from altair import Chart

from data.data_loading import load_db_table, load_db_query


@st.cache(ttl=60*60*24)
def df_to_csv(df: pd.DataFrame) -> bytes:
    """Cached conversion of df to csv"""
    csv = df.to_csv().encode('utf-8')
    return csv


def download_button(
        csv: bytes,
        file_name: str,
        include_date: bool = True
) -> bytes:
    """Wrapper for streamlit's download button"""
    date_str = f'_{datetime.date.today().strftime("%Y-%m-%d")}' if include_date else ''
    return st.download_button(
        label="Click to download table",
        data=csv,
        file_name=f'{file_name}{date_str}.csv',
        mime='text/csv'
    )



class BasePage:
    def __init__(self):
        self.today = datetime.datetime.today()
        self.yesterday = self.today - datetime.timedelta(days=1)
        self.year = self.today.year
        self.date: Optional[datetime.date] = None
        self.df: Optional[pd.DataFrame] = None
        self.dataset: Optional[str] = None

    def run(self):
        raise NotImplementedError

    @staticmethod
    def get_unique_values(
            df: pd.DataFrame,
            col: str,
            include_all: bool = False
    ) -> List[Any]:
        """
        Return a sorted list of unique values for the selected column in dataframe

        Args:
            df (pd.DataFrame): dataframe
            col (str): column from which to pull values
            include_all (bool): if true, adds 'all' to the returned list

        Returns:
            (list): list of column's unique values
        """
        unique_values = df[col].unique().tolist()
        unique_values.sort(key=lambda x: (x is None, x))
        return ["all"] + unique_values if include_all else unique_values

