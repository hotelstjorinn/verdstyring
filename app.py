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
    # Við prófum nákvæma slóð fyrir Booking API (Api Dojo)
    url = f"https://{API_HOST}/locations/v3/search"
    querystring = {"text": leitar_ord, "locale": "is"}
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        
        # Ef við fáum villu frá RapidAPI (t.d. búið með kvóta)
        if "message" in data:
            st.sidebar.error(f"Skilaboð frá kerfi: {data['message']}")
        
        results = data.get('data', [])
        if not results:
            st.sidebar.warning("Engar niðurstöður fundust. Prófaðu annað nafn.")
            
        for item in results:
            if item.get('type') == 'hotel':
                name = item.get('title')
                h_id = item.get('id')
                if st.sidebar.button(f"➕ {name}", key=h_id):
                    st.session_state.min_hotel[name] = h_id
                    st.sidebar.success(f"Bætti við {name}!")
    except Exception as e:
        st.sidebar.error(f"Tæknileg villa: {e}")

# --- LISTINN ---
st.subheader("Gististaðir sem ég fylgist með")
if st.session_state.min_hotel:
    df = pd.DataFrame(list(st.session_state.min_hotel.items()), columns=['Nafn', 'ID'])
    st.table(df)
else:
    st.info("Listinn er tómur.")
