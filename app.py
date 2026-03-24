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
        res = requests.get(f"https://{API_HOST}/locations/auto-complete", 
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
    for nafn, h_id in list(st.session_state.min_hotel.items()):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"🏨 **{nafn}** (ID: {h_id})")
        with col2:
            if st.button("❌ Eyða", key=f"del_{h_id}"):
                del st.session_state.min_hotel[nafn]
                st.rerun()
    
    st.divider()

    colA, colB, colC = st.columns(3)
    btn_1_dagur = colA.button("Sækja verð markaðar núna")
    btn_7_dagar = colB.button("Sækja verð markaðar næstu 7 daga")
    btn_30_dagar = colC.button("Sækja verð markaðar næstu 30 daga")

    dagar_til_ad_saekja = 0
    if btn_1_dagur: dagar_til_ad_saekja = 1
    elif btn_7_dagar: dagar_til_ad_saekja = 7
    elif btn_30_dagar: dagar_til_ad_saekja = 30

    if dagar_til_ad_saekja > 0:
        if dagar_til_ad_saekja > 1:
            st.warning(f"Sæki verð fyrir {dagar_til_ad_saekja} daga. Þetta getur tekið smá stund.")
            
        all_prices = []
        progress_bar = st.progress(0)
        total_steps = len(st.session_state.min_hotel) * dagar_til_ad_saekja
        current_step = 0

        with st.spinner(f"Sæki gögn fyrir {dagar_til_ad_saekja} daga..."):
            for nafn, h_id in st.session_state.min_hotel.items():
                for dagur in range(dagar_til_ad_saekja):
                    checkin_date = datetime.now() + timedelta(days=dagur)
                    checkout_date = checkin_date + timedelta(days=1)
                    
                    url = f"https://{API_HOST}/properties/detail"
                    
                    querystring = {
                        "hotel_id": h_id,
                        "arrival_date": checkin_date.strftime("%Y-%m-%d"),
                        "departure_date": checkout_date.strftime("%Y-%m-%d"),
                        "currencycode": "ISK" # Heimtum ISK
                    }
                    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST}
                    
                    try:
                        response = requests.get(url, headers=headers, params=querystring)
                        res_data = response.json()
                        
                        # Skoðum hvort gögnin séu í lista (eins og þú sendir) eða orðabók
                        if isinstance(res_data, list) and len(res_data) > 0:
                            hotel_data = res_data[0]
                        else:
                            hotel_data = res_data
                            
                        price = 0
                        status = "Laust"
                        
                        # Athugum hvort hótelið sé uppselt
                        if hotel_data.get('soldout') == 1 or hotel_data.get('available_rooms') == 0:
                            status = "Uppselt"
                            # Reynileum að finna alternate_availability verðið (er oftast í öðrum gjaldmiðli)
                            alt_avail = hotel_data.get('alternate_availability', [])
                            if alt_avail and len(alt_avail) > 0:
                                price = alt_avail[0].get('price', 0)
                                if hotel_data.get('currency_code') == 'EUR' or alt_avail[0].get('currency') == 'USD':
                                    # Einföld gisk-umreiknun ef það skilar USD eða EUR þrátt fyrir beiðni
                                    if alt_avail[0].get('currency') == 'USD':
                                        price = price * 140 
                                    elif alt_avail[0].get('currency') == 'EUR':
                                        price = price * 150
                        else:
                            # Hér leitum við að venjulegu verði ef laust
                            try:
                                # Leita að samsettu verði
                                price = hotel_data.get('composite_price_breakdown', {}).get('gross_amount', {}).get('value', 0)
                                # Ef ekki þar, leita í price_breakdown
                                if price == 0:
                                   price = hotel_data.get('price_breakdown', {}).get('gross_price', 0)
                                # Ef ekki þar, reyna aðrar algengar staðsetningar í þessu API
                                if price == 0:
                                    price = hotel_data.get('min_total_price', 0)
                            except:
                                pass

                        all_prices.append({
                            "Dagsetning": checkin_date.strftime("%d.%m"),
                            "Hótel": nafn.split(',')[0], 
                            "Verð (ISK)": float(price),
                            "Staða": status
                        })
                        
                    except Exception as e:
                        all_prices.append({"Dagsetning": checkin_date.strftime("%d.%m"), "Hótel": nafn.split(',')[0], "Verð (ISK)": 0, "Staða": "Villa"})
                    
                    current_step += 1
                    progress_bar.progress(current_step / total_steps)

        # Birta niðurstöður
        df_prices = pd.DataFrame(all_prices)
        
        st.subheader(f"Verðyfirlit ({dagar_til_ad_saekja} daga)")
        
        # Sýnum töfluna alltaf svo þú sjáir hvort það sé uppselt
        st.dataframe(df_prices, use_container_width=True)
        
        # Gerum línurit bara fyrir þá sem eru með verð
        df_valid = df_prices[df_prices["Verð (ISK)"] > 0]
        
        if not df_valid.empty:
            if dagar_til_ad_saekja > 1:
                pivot_df = df_valid.pivot(index='Dagsetning', columns='Hótel', values='Verð (ISK)')
                st.line_chart(pivot_df)
            else:
                st.bar_chart(df_valid.set_index("Hótel")["Verð (ISK)"])
                
            meðaltal = df_valid["Verð (ISK)"].mean()
            st.metric("Meðalverð markaðar (þar sem er laust/verð)", f"{meðaltal:,.0f} ISK")
        else:
            st.warning("Ekkert gilt verð fannst (líklega allt uppselt á þessum dögum). Sjá töfluna að ofan.")

else:
    st.info("Listinn þinn er tómur. Notaðu leitina vinstra megin.")
