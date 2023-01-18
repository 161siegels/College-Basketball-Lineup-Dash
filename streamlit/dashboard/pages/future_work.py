import streamlit as st

from dashboard.pages.base import BasePage
import pathlib


class FutureWorkPage(BasePage):
    def __init__(self):
        super().__init__()

    def run(self):
        st.title('Future Work')
        left, right = st.columns([7, 3])
        with left:
            st.header("Improvements to current App")
            st.write("""- Include expected points (player-dependent) and/or shot quality (player independent)
                        \n- Include how Stanford performs vs other team going big or small
                        \n- Filter teams by KenPom rating. Show how Stanford performs compared to top 25 KenPom
                        \n- Player specific shot charts and impact stats- can include own RAPM ratings or external
                        \n- Fully customizable- can add whatever staff desires""")
            st.header("Possibilities with synergy")
            st.write("""- Much better expected points (more specific tagging, shot location for all shots)
                        \n- More specific visualizations of efficiency and frequency of certain shots
                        \n- Can look at on-ball defenders
                        \n- Off/Def stats from different actions (cuts, pnr, etc)
                        \n- Man vs Zone analysis
                        \n- Potential assists (valuable playmaking stat but need FromPlayerId for all shots)
                        \n- HS and AAU data provide an opportunity to generate independent recruit rankings""")
            st.header("Other Poential Ideas (High Level)")
            st.write("""1. Scouting reports- player/team specific breakdowns of tendencies and efficiencies
                        \n\n2. End of game scenarios- Win probability model to capture end of game strategy. Visualizations to 
                        easily capture what the optimal strategy is for end of game (http://stats.inpredictable.com/nba/wpBox_live.php)
                        \n\n3. RAPM (Regularized Adjusted Plus Minus) Style Model for Player, Team Ratings
                        \n\t  a. Opponent adjusted player/team ratings for usage offense, playmaking offense, on vs
                        off ball defense, pace
                        \n\t  b. Could be huge help in recruiting to find gems (like Mike Jones) in the transfer portal""")

        with right:
            with open(f'{pathlib.Path().absolute()}/data/logo2.png', "rb") as image_file:
                encoded_string = image_file.read()
            st.image(encoded_string)