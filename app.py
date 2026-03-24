import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Mín Verðstýring", layout="wide")

# 1. Öryggisathugun á lyklum
try:
    API_KEY = st.secrets["api_key"]
    API_HOST = st.secrets["api_host"]
except:
    st.error("⚠️ API lykill vantar! Farðu í Settings -> Secrets í Streamlit og settu hann inn.")
    st.stop()

st.title("🏨 Mín Verðstýring - Stjórnborð")

# 2. Búa til geymslu fyrir hótelin þín (svo þau hverfi ekki)
if 'min_hotel' not in st.session_state:
    st.session_state.min_hotel = {}

# 3. LEITARKASSI (Hliðarstika)
st.sidebar.header("🔍 Leita að gististað")
leitar_ord = st.sidebar.text_input("Skrifaðu nafn (t.d. B59 eða Hamar):")

if st.sidebar.button("Leita núna"):
    # Við notum 'locations/v3/search' til að finna rétta staði
    search_url = f"https://{API_HOST}/locations/v3/search"
    params = {"text": leitar_ord, "locale": "is"}
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST}
    
    try:
        res = requests.get(search_url, headers=headers, params=params)
        data = res.json()
        
        st.sidebar.write("Niðurstöður:")
        # Sýnum aðeins gististaði (hotels) úr leitinni
        for item in data.get('data', []):
            if item.get('type') == 'hotel':
                name = item.get('title')
                h_id = item.get('id')
                # Búum til takka fyrir hvert hótel
                if st.sidebar.button(f"➕ Bæta við: {name}", key=h_id):
                    st.session_state.min_hotel[name] = h_id
                    st.sidebar.success(f"{name} bætist á listann!")
    except:
        st.sidebar.error("Villa við leit. Athugaðu tengingu.")

# 4. BIRTING Á LISTANUM ÞÍNUM
st.subheader("Gististaðir sem ég fylgist með")

if st.session_state.min_hotel:
    # Búum til töflu yfir það sem þú ert með á listanum
    h_listi = []
    for nafn, id_nr in st.session_state.min_hotel.items():
        h_listi.append({"Nafn": nafn, "Hotel ID": id_nr})
    
    st.table(pd.DataFrame(h_listi))
    
    # 5. HNAPPUR FYRIR 30 DAGA GREININGU
    if st.button("📊 Greina 30 daga meðalverð markaðar"):
        st.info("Hérna mun appið sækja 30 daga verð fyrir alla staðina á listanum þínum...")
        # (Næsta skref er að virkja verðsöfnunina hér)
else:
    st.info("Listinn þinn er tómur. Notaðu leitina vinstra megin til að finna hótel.")

if st.button("Hreinsa allan listann"):
    st.session_state.min_hotel = {}
    st.rerun()
