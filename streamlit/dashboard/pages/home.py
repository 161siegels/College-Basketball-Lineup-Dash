import streamlit as st

from dashboard.pages.base import BasePage
import pathlib


class HomePage(BasePage):
    def __init__(self):
        super().__init__()

    def run(self):
        left, _, right = st.columns([7, 1, 2])
        with left:
            st.title('Stanford Basketball Eval Home')
            st.write('''Welcome to Stanford Basketball Analytics Streamlit! 
            Click the radio to the left to navigate to the pages outlined below:''')
            st.subheader('Shot Chart')
            st.write('''Shot Charts using ESPN shot location data and NCAA PBP.
                        Shows rolled up summary rate stats from the play by play.
                        Can filter on teams and players on/off''')
            st.subheader('Team Summary Chart')
            st.write('''Team summary charts similar to the ones displayed in shot chart
                        table. However, this also allows for analysis of small lineups
                        and big lineups. Simple view with downloadable data''')
            st.subheader('Lineups')
            st.write('''This view shows all 1, 2, 3, 4, 5-man lineup combinations for a given
                        team and their stats. Can view how each past lineup has done relative to
                        their competition. Also easily downloadable data.
                        ''')
        with right:
            with open(f'{pathlib.Path().absolute()}/data/logo2.png', "rb") as image_file:
                encoded_string = image_file.read()
            st.image(encoded_string)

