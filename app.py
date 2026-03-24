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
            search_type = data_loc[0].get("dest_type", "city") 
            fundid_nafn = data_loc[0].get("name", hotel)
            
            st.info(f"📍 Tengdi '{hotel}' við: **{fundid_nafn}** (ID: {dest_id}, Tegund: {search_type})")
            
            for i in range(fjoldi_daga):
                checkin_dagur = idag + datetime.timedelta(days=i)
                checkout_dagur = checkin_dagur + datetime.timedelta(days=1)
                
                verd = 0 
                
                if search_type == "hotel":
                    url_api = "https://apidojo-booking-v1.p.rapidapi.com/properties/v2/get-rooms"
                    qs_api = {
                        "hotel_id": str(dest_id),
                        "arrival_date": checkin_dagur.strftime("%Y-%m-%d"),
                        "departure_date": checkout_dagur.strftime("%Y-%m-%d"),
                        "rec_guest_qty": "2",
                        "rec_room_qty": "1",
                        "currency_code": "ISK"
                    }
                    res_api = requests.get(url_api, headers=headers, params=qs_api)
                    data_api = res_api.json()
                    
                    if isinstance(data_api, list) and len(data_api) > 0:
                        first_item = data_api[0]
                        
                        # NÝJA AÐFERÐIN: Finnum grunnverðið (Gross Amount) úr öllum herbergjum
                        # Þetta hunsar sérstök farsíma-tilboð og líkir betur eftir borðtölvu!
                        verd_listi = []
                        if "block" in first_item and isinstance(first_item["block"], list):
                            for b in first_item["block"]:
                                if "product_price_breakdown" in b:
                                    ppb = b["product_price_breakdown"]
                                    if "gross_amount" in ppb and "value" in ppb["gross_amount"]:
                                        verd_listi.append(ppb["gross_amount"]["value"])
                        
                        if verd_listi:
                            verd = min(verd_listi) # Velur ódýrasta grunnverðið sem er í boði
                
                else:
                    url_api = "https://apidojo-booking-v1.p.rapidapi.com/properties/list"
                    qs_api = {
                        "offset": "0",
                        "arrival_date": checkin_dagur.strftime("%Y-%m-%d"),
                        "departure_date": checkout_dagur.strftime("%Y-%m-%d"),
                        "guest_qty": "2", 
                        "room_qty": "1",  
                        "dest_ids": str(dest_id),  
                        "search_type": search_type, 
                        "price_filter_currencycode": "ISK",
                        "children_qty": "0"
                    }
                    res_api = requests.get(url_api, headers=headers, params=qs_api)
                    data_api = res_api.json()
                    
                    if "result" in data_api and len(data_api["result"]) > 0:
                        hotel_data = data_api["result"][0]
                        if "composite_price_breakdown" in hotel_data and "gross_amount" in hotel_data["composite_price_breakdown"]:
                            verd = hotel_data["composite_price_breakdown"]["gross_amount"].get("value", 0)
                        elif "priceBreakdown" in hotel_data and "grossPrice" in hotel_data["priceBreakdown"]:
                            verd = hotel_data["priceBreakdown"]["grossPrice"].get("value", 0)
                        elif "min_total_price" in hotel_data:
                            verd = hotel_data.get("min_total_price", 0)

                if not verd or verd == 0:
                    with st.expander(f"🔍 Fann ekki verð fyrir {checkin_dagur.strftime('%d.%m')} - Smelltu til að sjá Gögn"):
                         st.write("Vélin fékk þessi gögn en gat ekki pikkað verðið út:")
                         st.json(data_api)
                
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
                
                df['Verð sýnt'] = df['Verð (ISK)'].apply(
                    lambda x: f"{x:,}".replace(",", ".") if x > 0 else ""
                )
                
                df['Dagsetning_str'] = pd.to_datetime(df['Dagsetning']).dt.strftime("%d.%m")
                df.index = np.arange(1, len(df) + 1)

                st.subheader(f"Verðyfirlit ({dagar_valdir} dagar)")
                
                syndir_dalkar = [
                    'Dagsetning_str', 'Hótel', 'Fjöldi herbergja', 'Verð sýnt', 'Staða'
                ]
                st.dataframe(df[syndir_dalkar], use_container_width=True)

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
                    
                    df_saman['Venjulegt meðalverð'] = df_saman['Venjulegt meðalverð'].round(0).astype(int)
                    df_saman['Vegið meðalverð'] = df_saman['Vegið meðalverð'].round(0).astype(int)

                    df_saman['Venjulegt (sýnt)'] = df_saman['Venjulegt meðalverð'].apply(
                        lambda x: f"{x:,} ISK".replace(",", ".")
                    )
                    df_saman['Vegið (sýnt)'] = df_saman['Vegið meðalverð'].apply(
                        lambda x: f"{x:,} ISK".replace(",", ".")
                    )
                    df_saman.index = np.arange(1, len(df_saman) + 1)
                    
                    syndir_dalkar_saman = ['Dagsetning_str', 'Venjulegt (sýnt)', 'Vegið (sýnt)']
                    st.dataframe(df_saman[syndir_dalkar_saman], use_container_width=True)

                    st.subheader("Verðþróun")
                    fig = px.bar(df, x='Dagsetning_str', y='Verð (ISK)', color='Hótel', barmode='group')
                    
                    fig.add_scatter(
                        x=df_saman['Dagsetning_str'], y=df_saman['Venjulegt meðalverð'], 
                        mode='lines+markers', name='Venjulegt meðaltal', 
                        line=dict(color='black', dash='dash', width=2)
                    )
                    
                    fig.add_scatter(
                        x=df_saman['Dagsetning_str'], y=df_saman['Vegið meðalverð'], 
                        mode='lines+markers', name='Vegið meðaltal', 
                        line=dict(color='red', width=3)
                    )
                    
                    fig.update_yaxes(rangemode="tozero")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Ekkert verð fannst (Flettu upp í API svarinu hér að ofan til að sjá ástæðuna).")
        else:
            st.error("Þú þarft að bæta við að minnsta kosti einum gististað vinstra megin áður en þú leitar!")

if __name__ == "__main__":
    main()
