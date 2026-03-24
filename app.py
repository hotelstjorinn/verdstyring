import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px

st.set_page_config(page_title="Verðstýring", layout="wide")

# 1. Öryggisathugun
try:
    API_KEY = st.secrets["api_key"]
    API_HOST = st.secrets["api_host"]
except:
    st.error("⚠️ API lykill vantar í Secrets!")
    st.stop()

st.title("🏨 Mín Verðstýring - Stjórnborð")

if 'min_hotel' not in st.session_state:
    st.session_state.min_hotel = {}

# --- HLIÐARSTIKA ---
st.sidebar.header("🔍 Leita að gististað")
leitar_ord = st.sidebar.text_input("Nafn hótels:", key="search_input")

if leitar_ord:
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST}
    try:
        res = requests.get("https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete", 
                           headers=headers, params={"text": leitar_ord, "languagecode": "is"})
        data = res.json()
        for item in data:
            if item.get('dest_type') == 'hotel':
                nafn, h_id = item.get('label'), item.get('dest_id')
                if st.sidebar.button(f"➕ Bæta við {nafn[:30]}...", key=f"btn_{h_id}"):
                    st.session_state.min_hotel[nafn] = h_id
                    st.rerun()
    except:
        pass

# --- AÐALGLUGGI ---
st.subheader("Gististaðir í vöktun")

if st.session_state.min_hotel:
    # LÖGUM NÚMERUN: Búum til DataFrame og breytum index
    df_listi = pd.DataFrame([{"Nafn": k, "Booking ID": v} for k, v in st.session_state.min_hotel.items()])
    df_listi.index = df_listi.index + 1  # Byrjar á 1 í stað 0
    st.table(df_listi)
    
    st.divider()

    # --- SÆKJA 30 DAGA VERÐ ---
    if st.button("📊 Sækja 30-daga verðgreiningu núna"):
        all_prices = []
        progress_bar = st.progress(0)
        total = len(st.session_state.min_hotel)
        
        with st.spinner("Sæki rauntímaverð fyrir næstu 30 daga..."):
            for i, (nafn, h_id) in enumerate(st.session_state.min_hotel.items()):
                # Sækjum verðupplýsingar
                url = f"https://{API_HOST}/properties/get-details"
                
                # Við spyrjum um verð fyrir næstu 30 daga
                checkin = datetime.now().strftime("%Y-%m-%d")
                checkout = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                
                querystring = {"hotel_id": h_id, "checkin_date": checkin, "checkout_date": checkout, "currency": "ISK"}
                headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST}
                
                try:
                    response = requests.get(url, headers=headers, params=querystring)
                    res_data = response.json()
                    # Náum í verðið (þetta er dæmi, byggt á API svari)
                    price = res_data['data']['property']['v2_listing_cards'][0]['price_details']['gross_amount']['amount_unformatted']
                    all_prices.append({"Hótel": nafn.split(',')[0], "Verð": price, "Dagur": "Í dag"})
                except:
                    all_prices.append({"Hótel": nafn.split(',')[0], "Verð": 0, "Dagur": "Villa"})
                
                progress_bar.progress((i + 1) / total)

        # Sýna niðurstöður
        df_prices = pd.DataFrame(all_prices)
        st.subheader("Markaðsverð núna")
        st.bar_chart(df_prices.set_index("Hótel")["Verð"])
        
        meðaltal = df_prices[df_prices["Verð"] > 0]["Verð"].mean()
        st.metric("Meðalverð markaðar", f"{meðaltal:,.0f} ISK")
        st.success(f"💡 Ráðlagt verð fyrir þig (95% af meðaltali): {meðaltal * 0.95:,.0f} ISK")

else:
    st.info("Listinn þinn er tómur.")

if st.button("Hreinsa allan listann"):
    st.session_state.min_hotel = {}
    st.rerun()
