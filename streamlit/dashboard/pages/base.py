import datetime
from typing import *

import pandas as pd
import streamlit as st
from altair import Chart

from data.data_loading import load_db_table, load_db_query
from plotting.plotting_helpers import grouped_line_chart


@st.cache(ttl=60*60*24)
def load_db_table_as_df_cached(table) -> pd.DataFrame:
    """Cached version of the load_db_table_as_df function"""
    return load_db_table(table)


@st.cache(ttl=60*60*24)
def load_db_query_as_df_cached(query) -> pd.DataFrame:
    """Cached version of the load_db_query_as_df function"""
    return load_db_query(query)


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


def pivot_display(
        pivot_help: str,
        bin_help: str,
        pivot_vals: List[str],
        bin_cols: List[str]
) -> Tuple[str, int]:
    """Wrapper for radio/input options for pivot tables"""
    q = 0
    pivot = st.radio(
        label='Select grouping/pivot:',
        options=pivot_vals,
        help=pivot_help
    )
    if pivot in bin_cols:
        q = st.number_input(
            label='Bins:',
            min_value=1,
            max_value=50,
            value=10,
            step=1,
            help=bin_help
        )
    return pivot, q


def create_pivot_display(
        pivot_vals: List[str],
        bin_cols: List[str],
        pivot_help: str = None
) -> Tuple[str, Optional[str], int, Optional[int]]:
    """Return pivot and q (bin) options for use in Inplay and Live pages"""
    bin_help = 'Number of bins for first index, roughly of equal size.'
    pivot1, q1 = pivot_display(
        pivot_help=pivot_help,
        bin_help=bin_help,
        pivot_vals=pivot_vals,
        bin_cols=bin_cols
    )
    pivot2, q2 = None, None
    pivot_bool = st.checkbox(
        label='Pivot on second variable?',
        help='Create a multi-indexed pivot table. '
             "Changing the 'Display option' can help with viewing."
    )
    if pivot_bool:
        pivot_help = 'Use the selected column above as the first index and the selected below as the second.'
        bin_help = 'Number of bins for second index.'
        pivot2, q2 = pivot_display(
            bin_help=bin_help,
            pivot_help=pivot_help,
            pivot_vals=pivot_vals,
            bin_cols=bin_cols
        )
    return pivot1, pivot2, q1, q2


def df_display() -> Callable:
    """Display a radio for df display preference and return the corresponding streamlit function"""
    display = st.radio(
        label='Display options:',
        options=['Table', 'Dataframe'],
        help="'Table' displays the entirety of the dataframe. "
             "'Dataframe' displays a smaller dataframe with the ability to scroll."
    )
    display_func = st.dataframe if display == 'Dataframe' else st.table
    return display_func


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

    @staticmethod
    def layered_plot(
            df: pd.DataFrame,
            value_vars: list,
            id_vars: list,
            highlight: bool = True,
            **kwargs
    ) -> Chart:
        """
        Create a layered line plot

        Args:
            df (pd.DataFrame): dataframe
            value_vars (list): columns containing y-axis values for plotting
            id_vars (list): columns to use as identifier variables when melting df
            highlight (bool): if true, allows for individual lines on plot to be highlighted

        Returns:
            (altair.Chart) line chart
        """
        melted_df = pd.melt(
            df,
            id_vars=id_vars,
            value_vars=value_vars,
            var_name='Stat',
            value_name='Value'
        )
        layered_plot = grouped_line_chart(
            data=melted_df,
            y_col="Value",
            config=False,
            highlight=highlight,
            date_disp="yearmonthdate",
            **kwargs
        )
        return layered_plot
