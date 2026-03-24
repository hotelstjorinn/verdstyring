mport streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Verðstýring", layout="wide")

# Sækjum lykla úr Secrets
try:
    API_KEY = st.secrets["api_key"]
    API_HOST = st.secrets["api_host"]
except:
    st.error("⚠️ API lykill vantar í Secrets!")
    st.stop()

st.title("🏨 Mín Verðstýring - Stjórnborð")

# Búum til varanlegan lista í minni appsins
if 'min_hotel' not in st.session_state:
    st.session_state.min_hotel = {}

# --- HLIÐARSTIKA: LEIT ---
st.sidebar.header("🔍 Leita að gististað")
leitar_ord = st.sidebar.text_input("Nafn hótels:", key="search_input")

if leitar_ord:
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": API_HOST
    }
    
    try:
        # Sækjum niðurstöður
        res = requests.get("https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete", 
                           headers=headers, 
                           params={"text": leitar_ord, "languagecode": "is"})
        data = res.json()
        
        st.sidebar.write("Niðurstöður:")
        
        # Búum til takka fyrir hvern stað
        for item in data:
            if item.get('dest_type') == 'hotel':
                nafn = item.get('label')
                h_id = item.get('dest_id')
                
                # Þessi lína bætir við á listann þegar smellt er
                if st.sidebar.button(f"➕ Bæta við {nafn[:30]}...", key=f"btn_{h_id}"):
                    st.session_state.min_hotel[nafn] = h_id
                    st.sidebar.success(f"Bætti við {nafn.split(',')[0]}!")
                    st.rerun() # Endurræsum til að sýna töfluna strax
    except:
        pass

# --- AÐALGLUGGI: LISTINN ÞINN ---
st.subheader("Gististaðir í vöktun")

if st.session_state.min_hotel:
    # Sýnum listann í flottri töflu
    df = pd.DataFrame([
        {"Nafn": k, "Booking ID": v} for k, v in st.session_state.min_hotel.items()
    ])
    st.dataframe(df, use_container_width=True)
    
    st.divider()
    
    # Hér kemur næsta stóra skref:
    if st.button("📊 Sækja 30-daga verðgreiningu fyrir þessa staði"):
        st.warning("Næsta skref: Tengja raunverulega verðsöfnun fyrir valda staði.")
else:
    st.info("Listinn þinn er tómur. Notaðu leitina vinstra megin til að fylla hann.")

if st.button("Hreinsa allan listann"):
    st.session_state.min_hotel = {}
    st.rerun()
