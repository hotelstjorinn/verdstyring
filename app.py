import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
# GERVIGÖGN - Núna með "Fjölda herbergja" til að geta reiknað vegið meðaltal
def saekja_gervigogn(hotel_listi, fjoldi_daga):
    idag = datetime.date.today()
    gogn = []
    
    # Búum til fastan fjölda herbergja (vægi) fyrir hvert hótel í þessari leit
    hotel_staerdir = {hotel: np.random.randint(20, 150) for hotel in hotel_listi}
    
    for hotel in hotel_listi:
        herbergi = hotel_staerdir[hotel]
        for i in range(fjoldi_daga):
            dagur = idag + datetime.timedelta(days=i)
            verd = np.random.choice([0, 24846, 32638, 15000, 28000, 42000]) 
            gogn.append({"Dagsetning": dagur, "Hótel": hotel, "Verð (ISK)": verd, "Fjöldi herbergja": herbergi})
    return pd.DataFrame(gogn)
# ==========================================

def main():
    st.title("🏨 Hótelstjórinn markaðsverð")

    if 'valin_hotel' not in st.session_state:
        st.session_state['valin_hotel'] = []

    # --- HLIÐARSTIKA (LEIT OG LISTI) ---
    st.sidebar.header("Leit")
    
    nytt_hotel = st.sidebar.text_input("Bæta við gististað (ýttu á Enter)")
    
    if nytt_hotel and nytt_hotel not in st.session_state['valin_hotel']:
        st.session_state['valin_hotel'].append(nytt_hotel)

    if len(st.session_state['valin_hotel']) > 0:
        st.sidebar.markdown("### Valdir gististaðir:")
        for i, hotel in enumerate(st.session_state['valin_hotel']):
            st.sidebar.markdown(f"- **{hotel}**")
            
        if st.sidebar.button("Hreinsa allan lista"):
            st.session
