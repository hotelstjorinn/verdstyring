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

    # --- HNAPPARNIR ÞRÍR ---
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
        
        debug_data = None

        with st.spinner(f"Sæki gögn fyrir {dagar_til_ad_saekja} daga..."):
            for nafn, h_id in st.session_state.min_hotel.items():
                for dagur in range(dagar_til_ad_saekja):
                    checkin_date = datetime.now() + timedelta(days=dagur)
                    checkout_date = checkin_date + timedelta(days=1)
                    
                    # RÉTT SLÓÐ FYRIR ÞETTA API ER '/properties/list'
                    url = f"https://{API_HOST}/properties/list"
                    querystring = {
                        "dest_id": h_id,
                        "dest_type": "hotel",
                        "arrival_date": checkin_date.strftime("%Y-%m-%d"),
                        "departure_date": checkout_date.strftime("%Y-%m-%d"),
                        "room_qty": "1",
                        "guest_qty": "2",
                        "currencycode": "ISK"
                    }
                    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST}
                    
                    try:
                        response = requests.get(url, headers=headers, params=querystring)
                        res_data = response.json()
                        
                        price = 0
                        try:
                            # Hér finnum við verðið í nýja svarinu frá API-inu
                            results = res_data.get('result', [])
                            if results and len(results) > 0:
                                hotel_data = results[0]
                                price = hotel_data.get('min_total_price', 0)
                                if price == 0:
                                    # Varakostur ef verðið heitir eitthvað annað
                                    price = hotel_data.get('composite_price_breakdown', {}).get('gross_amount', {}).get('value', 0)
                        except:
                            pass
                        
                        if price == 0 and debug_data is None:
                            debug_data = res_data

                        all_prices.append({
                            "Dagsetning": checkin_date.strftime("%d.%m"),
                            "Hótel": nafn.split(',')[0], 
                            "Verð": price
                        })
                    except Exception as e:
                        all_prices.append({"Dagsetning": checkin_date.strftime("%d.%m"), "Hótel": nafn.split(',')[0], "Verð": 0})
                    
                    current_step += 1
                    progress_bar.progress(current_step / total_steps)

        # Birta niðurstöður
        df_prices = pd.DataFrame(all_prices)
        
        st.subheader(f"Verðyfirlit ({dagar_til_ad_saekja} daga)")
        
        df_valid = df_prices[df_prices["Verð"] > 0]
        
        if not df_valid.empty:
            if dagar_til_ad_saekja > 1:
                pivot_df = df_valid.pivot(index='Dagsetning', columns='Hótel', values='Verð')
                st.line_chart(pivot_df)
            else:
                st.bar_chart(df_valid.set_index("Hótel")["Verð"])
                
            meðaltal = df_valid["Verð"].mean()
            st.metric("Meðalverð", f"{meðaltal:,.0f} ISK")
        else:
            st.error("⚠️ Appið fær ennþá 0 kr. frá Booking API-inu.")
            st.write("Villan 'Endpoint does not exist' er nú farin, en hér eru nýju gögnin frá Booking. **Sendu mér skjáskot af gula kassanum ef hann birtist!**")
            if debug_data:
                st.json(debug_data)

else:
    st.info("Listinn þinn er tómur. Notaðu leitina vinstra megin.")
