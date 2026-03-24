import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Verðstýring", layout="wide")

try:
    API_KEY = st.secrets["api_key"]
    API_HOST = st.secrets["api_host"]
except:
    st.error("⚠️ API lykill vantar í Secrets!")
    st.stop()

st.title("🏨 Mín Verðstýring - Stjórnborð")

if 'min_hotel' not in st.session_state:
    st.session_state.min_hotel = {}

# --- HLIÐARSTIKA: LEIT ---
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
                if st.sidebar.button(f"➕ Bæta við {nafn[:30]}...", key=f"btn_add_{h_id}"):
                    st.session_state.min_hotel[nafn] = h_id
                    st.rerun()
    except:
        pass

# --- AÐALGLUGGI: LISTINN ÞINN ---
st.subheader("Gististaðir í vöktun")

if st.session_state.min_hotel:
    # Búum til lista með takka til að eyða
    for nafn, h_id in list(st.session_state.min_hotel.items()):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"🏨 **{nafn}** (ID: {h_id})")
        with col2:
            if st.button("❌ Eyða", key=f"del_{h_id}"):
                del st.session_state.min_hotel[nafn]
                st.rerun()
    
    st.divider()

    # --- SÆKJA VERÐ ---
    if st.button("📊 Sækja verð markaðar núna"):
        all_prices = []
        progress_bar = st.progress(0)
        total = len(st.session_state.min_hotel)
        
        with st.spinner("Sæki rauntímaverð..."):
            for i, (nafn, h_id) in enumerate(st.session_state.min_hotel.items()):
                # Notum "properties/list" sem er áreiðanlegra
                url = f"https://{API_HOST}/properties/list"
                
                checkin = datetime.now().strftime("%Y-%m-%d")
                checkout = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                
                querystring = {
                    "dest_id": h_id,
                    "search_type": "hotel",
                    "arrival_date": checkin,
                    "departure_date": checkout,
                    "currencycode": "ISK"
                }
                headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST}
                
                try:
                    response = requests.get(url, headers=headers, params=querystring)
                    res_data = response.json()
                    
                    # Reynum að finna verðið í niðurstöðunni
                    price = 0
                    if 'result' in res_data and len(res_data['result']) > 0:
                        # Þetta er algengasta staðsetningin á verði í þessu API
                        price = res_data['result'][0].get('min_total_price', 0)
                        
                    all_prices.append({"Hótel": nafn.split(',')[0], "Verð": price})
                except Exception as e:
                    all_prices.append({"Hótel": nafn.split(',')[0], "Verð": 0})
                
                progress_bar.progress((i + 1) / total)

        # Birta niðurstöður
        df_prices = pd.DataFrame(all_prices)
        st.subheader("Verð fyrir næstu nótt (ISK)")
        
        # Birtum aðeins þá sem skiluðu verði stærra en 0
        df_valid = df_prices[df_prices["Verð"] > 0]
        
        if not df_valid.empty:
            st.bar_chart(df_valid.set_index("Hótel")["Verð"])
            
            meðaltal = df_valid["Verð"].mean()
            st.metric("Meðalverð markaðar", f"{meðaltal:,.0f} ISK")
            st.success(f"💡 Ráðlagt verð fyrir þig (95% af meðaltali): {meðaltal * 0.95:,.0f} ISK")
        else:
            st.warning("Ekkert verð fannst. Hótelin gætu verið uppseld eða API-ið er ekki að skila gögnum á þessu formi.")
            st.dataframe(df_prices) # Sýna töfluna til að sjá hvar það klikkaði

else:
    st.info("Listinn þinn er tómur. Notaðu leitina vinstra megin.")
