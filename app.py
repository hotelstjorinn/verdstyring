import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import requests

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
def saekja_raungogn(hotel_listi, fjoldi_daga):
    API_KEY = "aa73991419msh780ae4bacd33dc3p12ac5fjsn494bf3cba6a6"
    idag = datetime.date.today()
    gogn = []
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"
    }
    
    for hotel in hotel_listi:
        try:
            url_loc = "https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete"
            qs_loc = {"text": hotel, "languagecode": "is"}
            
            res_loc = requests.get(url_loc, headers=headers, params=qs_loc)
            data_loc = res_loc.json()
            
            if not data_loc or len(data_loc) == 0:
                st.warning(f"Booking fann ekki gististaðinn: '{hotel}'")
                continue
                
            dest_id = data_loc[0].get("dest_id")
            search_type = data_loc[0].get("search_type")
            fundid_nafn = data_loc[0].get("name", hotel)
            
            st.info(f"📍 Tengdi '{hotel}' við: **{fundid_nafn}** (Booking ID: {dest_id})")
            
            for i in range(fjoldi_daga):
                checkin_dagur = idag + datetime.timedelta(days=i)
                checkout_dagur = checkin_dagur + datetime.timedelta(days=1)
                 
                url_list = "https://apidojo-booking-v1.p.rapidapi.com/properties/list"
                qs_list = {
                    "offset": "0",
                    "arrival_date": checkin_dagur.strftime("%Y-%m-%d"),
                    "departure_date": checkout_dagur.strftime("%Y-%m-%d"),
                    "guest_qty": "2", 
                    "room_qty": "1",  
                    "dest_ids": str(dest_id),  # <--- HÉR ER 'S'-IÐ KOMIÐ AFTUR!
                    "search_type": search_type,
                    "price_filter_currencycode": "ISK" 
                }
                
                res_list = requests.get(url_list, headers=headers, params=qs_list)
                data_list = res_list.json()
                
                verd = 0 
                
                if "result" in data_list and len(data_list["result"]) > 0:
                    hotel_data = data_list["result"][0]
                    if "min_total_price" in hotel_data:
                        verd = hotel_data.get("min_total_price", 0)
                    elif "price_breakdown" in hotel_data:
                        verd = hotel_data["price_breakdown"].get("gross_price", 0)
                    elif "composite_price_breakdown" in hotel_data:
                        verd = hotel_data["composite_price_breakdown"]["gross_amount"].get("value", 0)
                else:
                    # Villuleit: Skrifar út svarið frá Booking svo þú getir séð afhverju það er falið
                    with st.expander(f"Sjá afhverju {hotel} er uppselt þann {checkin_dagur.strftime('%d.%m')}"):
                        st.write("Skilaboð frá Booking:")
                        st.write(data_list.get("zero_results_message", "Ekkert herbergi fannst (Mögulega lágmarksdvöl)."))
                
                herbergi = 50 
                
                gogn.append({
                    "Dagsetning": checkin_dagur, 
                    "Hótel": hotel, 
                    "Verð (ISK)": verd, 
                    "Fjöldi herbergja": herbergi
                })
                    
        except Exception as e:
            st.error(f"Villa við að tengjast API fyrir {hotel}: {e}")
            
    return pd.DataFrame(gogn)
# ==========================================

def main():
    st.title("🏨 Hótelstjórinn markaðsverð")

    if 'valin_hotel' not in st.session_state:
        st.session_state['valin_hotel'] = []

    st.sidebar.header("Leit")
    
    nytt_hotel = st.sidebar.text_input("Bæta við gististað (ýttu á Enter)")
    
    if nytt_hotel and nytt_hotel not in st.session_state['valin_hotel']:
        st.session_state['valin_hotel'].append(nytt_hotel)

    if len(st.session_state['valin_hotel']) > 0:
        st.sidebar.markdown("### Valdir gististaðir:")
        for i, hotel in enumerate(st.session_state['valin_hotel']):
            st.sidebar.markdown(f"- **{hotel}**")
            
        if st.sidebar.button("Hreinsa allan lista"):
            st.session_state['valin_hotel'] = []
            st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        btn_1 = st.button("Sækja verð markaðar núna")
    with col2:
        btn_7 = st.button("Sækja verð markaðar næstu 7 daga")
    with col3:
        btn_30 = st.button("Sækja verð markaðar næstu 30 daga")

    dagar_valdir = 0
    if btn_1: dagar_valdir = 1
    elif btn_7: dagar_valdir = 7
    elif btn_30: dagar_valdir = 30

    if dagar_valdir > 0:
        if len(st.session_state['valin_hotel']) > 0:
            st.success(f"Sæki raungögn af Booking fyrir **{len(st.session_state['valin_hotel'])}** gististaði í **{dagar_valdir}** daga. Bíddu andartak...")
            
            df = saekja_raungogn(st.session_state['valin_hotel'], dagar_valdir) 

            if not df.empty:
                df['Staða'] = np.where(df['Verð (ISK)'] > 0, 'Laust', 'Uppselt')
                df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
                df['Verð sýnt'] = df['Verð (ISK)'].apply(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "")
                df['Dagsetning_str'] = pd.to_datetime(df['Dagsetning']).dt.strftime("%d.%m")
                df.index = np.arange(1, len(df) + 1)

                st.subheader(f"Verðyfirlit ({dagar_valdir} dagar)")
                st.dataframe(df[['Dagsetning_str', 'Hótel', 'Fjöldi herbergja', 'Verð sýnt', 'Staða']], use_container_width=True)

                st.subheader("Meðalverð markaðar (Venjulegt og Vegið)")
                df_laust = df[df['Verð (ISK)'] > 0].copy()
                
                if not df_laust.empty:
                    df_medaltal = df_laust.groupby('Dagsetning_str')['Verð (ISK)'].mean().reset_index()
                    df_medaltal.rename(columns={'Verð (ISK)': 'Venjulegt meðalverð'}, inplace=True)

                    df_laust['Verð_Vægi'] = df_laust['Verð (ISK)'] * df_laust['Fjöldi herbergja']
                    df_veg = df_laust.groupby('Dagsetning_str').agg(
                        Summa_Verð_Vægi=('Verð_Vægi', 'sum'),
                        Summa_Herbergi=('Fjöldi herbergja', 'sum')
                    ).reset_index()
                    df_veg['Vegið meðalverð'] = df_veg['Summa_Verð_Vægi'] / df_veg['Summa_Herbergi']

                    df_saman = pd.merge(df_medaltal, df_veg[['Dagsetning_str', 'Vegið meðalverð']], on='Dagsetning_str')
                    
                    df_saman['Venjulegt meðalverð'] = df_saman['Venjulegt meðalver
