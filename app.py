import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import requests
import io  

# ÞETTA VERÐUR AÐ VERA FYRSTA LÍNAN
st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
# LYKILORÐSKERFI
# ==========================================
def athuga_lykilord():
    def lykilord_slegid_inn():
        if st.session_state["lykilorð_input"] == "hotel123": 
            st.session_state["innskradur"] = True
            del st.session_state["lykilorð_input"]
        else:
            st.session_state["innskradur"] = False

    if "innskradur" not in st.session_state:
        st.title("🔒 Vinsamlegast skráðu þig inn")
        st.text_input("Lykilorð", type="password", on_change=lykilord_slegid_inn, key="lykilorð_input")
        return False
    elif not st.session_state["innskradur"]:
        st.title("🔒 Vinsamlegast skráðu þig inn")
        st.text_input("Lykilorð", type="password", on_change=lykilord_slegid_inn, key="lykilorð_input")
        st.error("😕 Rangt lykilorð, reyndu aftur.")
        return False
    else:
        return True

# ==========================================
# API GAGNASÖFNUN
# ==========================================
def saekja_raungogn(hotel_dict, fjoldi_daga):
    API_KEY = "aa73991419msh780ae4bacd33dc3p12ac5fjsn494bf3cba6a6"
    idag = datetime.date.today()
    gogn = []
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"
    }
    
    for hotel, herbergi in hotel_dict.items():
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
            
            st.info(f"📍 Tengdi '{hotel}' við: **{fundid_nafn}**")
            
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
                        verd_listi = []
                        if "block" in first_item and isinstance(first_item["block"], list):
                            for b in first_item["block"]:
                                if "product_price_breakdown" in b:
                                    ppb = b["product_price_breakdown"]
                                    if "gross_amount" in ppb and "value" in ppb["gross_amount"]:
                                        verd_listi.append(ppb["gross_amount"]["value"])
                        
                        if verd_listi:
                            verd = min(verd_listi) 
                
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

                gogn.append({
                    "Dagsetning_obj": checkin_dagur, 
                    "Hótel": hotel, 
                    "Verð (ISK)": verd,
                    "Fjöldi herbergja": herbergi
                })
                    
        except Exception as e:
            st.error(f"Villa við að tengjast API fyrir {hotel}: {e}")
            
    return pd.DataFrame(gogn)

# ==========================================
# AÐAL FORRITIÐ
# ==========================================
def main():
    st.title("🏨 Hótelstjórinn markaðsverð")

    if 'valin_hotel' not in st.session_state or isinstance(st.session_state['valin_hotel'], list):
        st.session_state['valin_hotel'] = {}

    st.sidebar.header("Leit")
    
    nytt_hotel = st.sidebar.text_input("Nafn á gististað")
    herbergjafjoldi = st.sidebar.number_input("Fjöldi herbergja á þessu hóteli", min_value=1, value=20, step=1)
    
    if st.sidebar.button("Bæta við á lista"):
        if nytt_hotel and nytt_hotel not in st.session_state['valin_hotel']:
            st.session_state['valin_hotel'][nytt_hotel] = herbergjafjoldi
            st.rerun()

    if len(st.session_state['valin_hotel']) > 0:
        st.sidebar.markdown("### Valdir gististaðir:")
        for hotel, f in st.session_state['valin_hotel'].items():
            st.sidebar.markdown(f"- **{hotel}** ({f} herb.)")
            
        if st.sidebar.button("Hreinsa allan lista"):
            st.session_state['valin_hotel'] = {}
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
                
                df['Dagsetning'] = pd.to_datetime(df['Dagsetning_obj']).dt.strftime("%d.%m")
                df.index = np.arange(1, len(df) + 1)

                st.subheader(f"Verðyfirlit ({dagar_valdir} dagar)")
                syndir_dalkar = ['Dagsetning', 'Hótel', 'Fjöldi herbergja', 'Verð sýnt', 'Staða']
                st.dataframe(df[syndir_dalkar], use_container_width=True)

                st.subheader("Meðalverð markaðar (Venjulegt vs. Vegið)")
                df_laust = df[df['Verð (ISK)'] > 0].copy()
                
                if not df_laust.empty:
                    df_medaltal = df_laust.groupby('Dagsetning')['Verð (ISK)'].mean().reset_index()
                    df_medaltal.rename(columns={'Verð (ISK)': 'Venjulegt'}, inplace=True)

                    df_laust['Verð_Vægi'] = df_laust['Verð (ISK)'] * df_laust['Fjöldi herbergja']
                    df_veg = df_laust.groupby('Dagsetning').agg(
                        Summa_Verð_Vægi=('Verð_Vægi', 'sum'),
                        Summa_Herbergi=('Fjöldi herbergja', 'sum')
                    ).reset_index()
                    df_veg['Vegið'] = df_veg['Summa_Verð_Vægi'] / df_veg['Summa_Herbergi']

                    df_saman = pd.merge(df_medaltal, df_veg[['Dagsetning', 'Vegið']], on='Dagsetning')
                    df_saman['Venjulegt'] = df_saman['Venjulegt'].round(0).astype(int)
                    df_saman['Vegið'] = df_saman['Vegið'].round(0).astype(int)

                    df_saman['Meðalverð'] = df_saman['Venjulegt'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
                    df_saman['Vegið meðalverð'] = df_saman['Vegið'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
                    
                    df_saman.index = np.arange(1, len(df_saman) + 1)
                    
                    syndir_dalkar_saman = ['Dagsetning', 'Meðalverð', 'Vegið meðalverð']
                    st.dataframe(df_saman[syndir_dalkar_saman], use_container_width=True)

                    st.subheader("Verðþróun")
                    fig = px.bar(df, x='Dagsetning', y='Verð (ISK)', color='Hótel', barmode='group')
                    
                    fig.add_scatter(
                        x=df_saman['Dagsetning'], y=df_saman['Venjulegt'], 
                        mode='lines+markers', name='Meðalverð', 
                        line=dict(color='black', dash='dash', width=2)
                    )
                    
                    fig.add_scatter(
                        x=df_saman['Dagsetning'], y=df_saman['Vegið'], 
                        mode='lines+markers', name='Vegið meðalverð', 
                        line=dict(color='red', width=3)
                    )
                    
                    fig.update_yaxes(rangemode="tozero")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # ==========================================
                    # EXCEL NIÐURHAL MEÐ SÚLURITI
                    # ==========================================
                    st.markdown("---")
                    st.subheader("📥 Sækja skýrslu")
                    
                    output = io.BytesIO()
                    
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # FLIPI 1: Öll gögnin
                        gogn_ut = df[['Dagsetning_obj', 'Hótel', 'Fjöldi herbergja', 'Verð (ISK)', 'Staða']].copy()
                        gogn_ut.rename(columns={'Dagsetning_obj': 'Dagsetning'}, inplace=True)
                        # Breytum í dagsetningar-format fyrir Excel
                        gogn_ut['Dagsetning'] = pd.to_datetime(gogn_ut['Dagsetning']).dt.date
                        gogn_ut.to_excel(writer, sheet_name='Öll gögn', index=False)
                        
                        # FLIPI 2: Meðalverð og SÚLURIT
                        medaltal_ut = df_saman[['Dagsetning', 'Venjulegt', 'Vegið']].copy()
                        medaltal_ut.rename(columns={'Venjulegt': 'Venjulegt meðalverð', 'Vegið': 'Vegið meðalverð'}, inplace=True)
                        medaltal_ut.to_excel(writer, sheet_name='Meðalverð Markaðar', index=False)
                        
                        # --- Hér búum við til ritið beint inn í Excel ---
                        workbook = writer.book
                        worksheet = writer.sheets['Meðalverð Markaðar']
                        
                        # Búum til nýtt súlurit ('column' = lóðréttar súlur)
                        chart = workbook.add_chart({'type': 'column'})
                        
                        max_row = len(medaltal_ut)
                        
                        # Bætum Venjulega meðalverðinu á grafið
                        chart.add_series({
                            'name':       ['Meðalverð Markaðar', 0, 1], # Nafnið er í dálki B, röð 1
                            'categories': ['Meðalverð Markaðar', 1, 0, max_row, 0], # Dagsetningar í dálki A
                            'values':     ['Meðalverð Markaðar', 1, 1, max_row, 1], # Tölurnar í dálki B
                            'fill':       {'color': '#4C78A8'} # Blár litur
                        })
                        
                        # Bætum Vegna meðalverðinu á grafið
                        chart.add_series({
                            'name':       ['Meðalverð Markaðar', 0, 2], # Nafnið er í dálki C, röð 1
                            'categories': ['Meðalverð Markaðar', 1, 0, max_row, 0], # Dagsetningar í dálki A
                            'values':     ['Meðalverð Markaðar', 1, 2, max_row, 2], # Tölurnar í dálki C
                            'fill':       {'color': '#E45756'} # Rauður litur
                        })
                        
                        # Stillingar á útlitinu
                        chart.set_title({'name': 'Meðalverð Markaðar (Súlurit)'})
                        chart.set_x_axis({'name': 'Dagsetning'})
                        chart.set_y_axis({'name': 'Verð (ISK)'})
                        chart.set_size({'width': 720, 'height': 400})
                        
                        # Setjum grafið inn á síðuna hægra megin við gögnin (í reit E2)
                        worksheet.insert_chart('E2', chart)
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label=f"Sækja Excel skýrslu ({dagar_valdir} dagar)",
                        data=excel_data,
                        file_name=f"markadsverd_{dagar_valdir}dagar_{datetime.date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                else:
                    st.warning("Ekkert verð fannst (Flettu upp í API svarinu hér að ofan til að sjá ástæðuna).")
        else:
            st.error("Þú þarft að bæta við að minnsta kosti einum gististað vinstra megin áður en þú leitar!")

# Keyrum lykilorðsvörnina Fyrst.
if athuga_lykilord():
    main()
