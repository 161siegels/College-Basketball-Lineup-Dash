import streamlit as st

from dashboard.pages.home import HomePage
from dashboard.pages.new_shot_chart import ShotChartPage
from dashboard.pages.lineups import LineupsPage
from dashboard.pages.summary_charts import SummaryChartPage
from dashboard.pages.future_work import FutureWorkPage

PAGES = {
    "Home": HomePage,
    "Shot Chart": ShotChartPage,
    "Team Summary Chart": SummaryChartPage,
    "Lineups": LineupsPage,
    "Future Work": FutureWorkPage
}


def main():
    st.set_page_config(layout="wide")
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", list(PAGES.keys()))
    PAGES[page]().run()
