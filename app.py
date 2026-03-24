import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Verðstýring", layout="wide")

# Sækjum lykla
try:
    API_KEY = st.secrets["api_key"]
    API_HOST = st.secrets["api_host"]
except:
    st.error("⚠️ API lykill vantar í Secrets!")
    st.stop()

st.title("🏨 Mín Verðstýring - Stjórnborð")

if 'min_hotel' not in st.session_state:
    st.session_state.min_hotel = {}

# --- LEITIN ---
st.sidebar.header("🔍 Leita að gististað")
leitar_ord = st.sidebar.text_input("Nafn hótels:")

if st.sidebar.button("Leita núna"):
    # BREYTT SLÓÐ HÉR: Prófum 'locations/search' í stað 'v3'
    url = f"https://{API_HOST}/locations/v3/search" # Ef þetta virkar ekki, prófum við v1 í næsta skrefi
    # Sum API nota 'v1/static/hotels' eða sambærilegt. 
    # Við prófum þessa sem er algengust:
    url_v1 = f"https://{API_HOST}/properties/list"
    
    querystring = {"name": leitar_ord, "locale": "is", "currency": "ISK"}
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }
    
    try:
        # Við notum einfaldari leitaraðferð sem flest Booking API styðja
        response = requests.get("https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete", 
                                headers=headers, 
                                params={"text": leitar_ord, "languagecode": "is"})
        data = response.json()
        
        st.sidebar.write("Niðurstöður:")
        found = False
        for item in data:
            if item.get('dest_type') == 'hotel':
                found = True
                name = item.get('label')
                h_id = item.get('dest_id')
                if st.sidebar.button(f"➕ {name}", key=h_id):
                    st.session_state.min_hotel[name] = h_id
                    st.sidebar.success(f"Bætti við {name}!")
        
        if not found:
            st.sidebar.warning("Fann engin hótel. Prófaðu að skrifa nákvæmara nafn.")
            
    except Exception as e:
        st.sidebar.error(f"Villa: {e}")

# --- LISTINN ---
st.subheader("Gististaðir sem ég fylgist með")
if st.session_state.min_hotel:
    df = pd.DataFrame(list(st.session_state.min_hotel.items()), columns=['Nafn', 'ID'])
    st.table(df)
else:
    st.info("Listinn er tómur.")
