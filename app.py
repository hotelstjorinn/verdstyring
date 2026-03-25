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
# LYKILORÐSKERFI OG UPPHAFIÐ
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
    # HÉR SETTURÐU INN NÝJA LYKILINN ÞINN EF ÞÚ ERT BÚIN(N) AÐ UPPAFÆRA!
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
            st.error(f"Villa við að tengjast API fyrir {hotel}. API kvóti gæti verið búinn. (Villa: {e})")
            
    return pd.DataFrame(gogn)

# ==========================================
# AÐAL FORRITIÐ
# ==========================================
def main():
    # 1. ATHUGUM HVORT "MITT HÓTEL" SÉ SKRÁÐ
    if "mitt_hotel_nafn" not in st.session_state:
        st.session_state["mitt_hotel_nafn"] = ""
        st.session_state["mitt_hotel_herb"] = 0

    if st.session_state["mitt_hotel_nafn"] == "":
        st.title("🏨 Velkomin(n) - Skráðu þitt hótel")
        st.write("Til að kerfið geti búið til réttar verðvísitölur og samanburðarskýrslur, byrjaðu á að skrá þitt eigið hótel.")
        
        m_nafn = st.text_input("Nafn á þínu hóteli (Eins og það heitir á Booking.com)")
        m_herb = st.number_input("Fjöldi herbergja á þínu hóteli", min_value=1, value=50, step=1)
        
        if st.button("Áfram á Mælaborð", type="primary"):
            if m_nafn:
                st.session_state["mitt_hotel_nafn"] = m_nafn
                st.session_state["mitt_hotel_herb"] = m_herb
                st.rerun()
            else:
                st.warning("Þú verður að skrifa nafn á hótelinu þínu.")
        return # Stoppar keyrslu hér þar til hótelið er skráð.

    # 2. MÆLABORÐIÐ HEFST
    st.title("📊 Hótelstjórinn - Verðvaktin")

    if 'keppinautar' not in st.session_state or isinstance(st.session_state['keppinautar'], list):
        st.session_state['keppinautar'] = {}

    st.sidebar.markdown(f"### 🏨 Mitt Hótel:\n**{st.session_state['mitt_hotel_nafn']}** ({st.session_state['mitt_hotel_herb']} herb.)")
    if st.sidebar.button("Breyta mínu hóteli"):
        st.session_state["mitt_hotel_nafn"] = ""
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.header("Leit að Keppinautum")
    
    nyr_keppinautur = st.sidebar.text_input("Nafn á keppinauti")
    kepp_herb = st.sidebar.number_input("Fjöldi herbergja (Keppinautur)", min_value=1, value=20, step=1)
    
    if st.sidebar.button("Bæta við keppinauti"):
        if nyr_keppinautur and nyr_keppinautur not in st.session_state['keppinautar']:
            # Pössum að notandi bæti ekki sjálfum sér við sem keppinauti
            if nyr_keppinautur.lower() != st.session_state['mitt_hotel_nafn'].lower():
                st.session_state['keppinautar'][nyr_keppinautur] = kepp_herb
                st.rerun()
            else:
                st.sidebar.error("Þú getur ekki sett þitt eigið hótel sem keppinaut.")

    if len(st.session_state['keppinautar']) > 0:
        st.sidebar.markdown("### Valdir keppinautar:")
        for k_hotel, k_f in st.session_state['keppinautar'].items():
            st.sidebar.markdown(f"- **{k_hotel}** ({k_f} herb.)")
            
        if st.sidebar.button("Hreinsa keppinauta"):
            st.session_state['keppinautar'] = {}
            st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        btn_1 = st.button("Sækja verð núna")
    with col2:
        btn_7 = st.button("Sækja verð næstu 7 daga")
    with col3:
        btn_30 = st.button("Sækja verð næstu 30 daga", type="primary")

    dagar_valdir = 0
    if btn_1: dagar_valdir = 1
    elif btn_7: dagar_valdir = 7
    elif btn_30: dagar_valdir = 30

    if dagar_valdir > 0:
        if len(st.session_state['keppinautar']) > 0:
            st.success(f"Sæki markaðsgögn fyrir þig og {len(st.session_state['keppinautar'])} keppinauta í {dagar_valdir} daga...")
            
            # Setjum Mitt hótel og Keppinauta saman í einn lista fyrir API leitina
            leitargogn = {st.session_state['mitt_hotel_nafn']: st.session_state['mitt_hotel_herb']}
            leitargogn.update(st.session_state['keppinautar'])
            
            df = saekja_raungogn(leitargogn, dagar_valdir) 

            if not df.empty:
                df['Staða'] = np.where(df['Verð (ISK)'] > 0, 'Laust', 'Uppselt')
                df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
                df['Dagsetning'] = pd.to_datetime(df['Dagsetning_obj']).dt.strftime("%d.%m")
                
                mitt_nafn = st.session_state['mitt_hotel_nafn']
                df_laust = df[df['Verð (ISK)'] > 0].copy()
                
                if not df_laust.empty:
                    # Skiljum að "Mitt hótel" og "Keppinauta"
                    df_mitt = df_laust[df_laust['Hótel'] == mitt_nafn].copy()
                    df_kepp = df_laust[df_laust['Hótel'] != mitt_nafn].copy()
                    
                    # Reiknum vegið meðalverð keppinauta
                    if not df_kepp.empty:
                        df_kepp['Verð_Vægi'] = df_kepp['Verð (ISK)'] * df_kepp['Fjöldi herbergja']
                        df_veg = df_kepp.groupby('Dagsetning').agg(
                            Summa_Verð_Vægi=('Verð_Vægi', 'sum'),
                            Summa_Herbergi=('Fjöldi herbergja', 'sum')
                        ).reset_index()
                        df_veg['Keppinautar_Meðalverð'] = (df_veg['Summa_Verð_Vægi'] / df_veg['Summa_Herbergi']).round(0).astype(int)
                    else:
                        df_veg = pd.DataFrame(columns=['Dagsetning', 'Keppinautar_Meðalverð'])
                    
                    # Tökum verðið mitt
                    if not df_mitt.empty:
                        df_mitt_einfalt = df_mitt[['Dagsetning', 'Verð (ISK)']].rename(columns={'Verð (ISK)': 'Mitt_Verð'})
                    else:
                        df_mitt_einfalt = pd.DataFrame(columns=['Dagsetning', 'Mitt_Verð'])

                    # Sameinum í eina skýrslu
                    df_skyrsla = pd.merge(df_veg[['Dagsetning', 'Keppinautar_Meðalverð']], df_mitt_einfalt, on='Dagsetning', how='outer').fillna(0)
                    
                    # REIKNUM VERÐVÍSITÖLU (PRICE INDEX)
                    # Vísitala > 100 þýðir að þú ert dýrari en markaðurinn. Vísitala < 100 þýðir að þú ert ódýrari.
                    df_skyrsla['Verðvísitala (%)'] = np.where(
                        (df_skyrsla['Keppinautar_Meðalverð'] > 0) & (df_skyrsla['Mitt_Verð'] > 0),
                        ((df_skyrsla['Mitt_Verð'] / df_skyrsla['Keppinautar_Meðalverð']) * 100).round(1),
                        0
                    )

                    st.markdown("---")
                    st.subheader("📈 Samanburður við Markaðinn")
                    
                    # Gerum línurit þar sem bara Mitt Hótel og Vegið Meðalverð sjást
                    fig = px.line(df_skyrsla, x='Dagsetning', y=['Mitt_Verð', 'Keppinautar_Meðalverð'], 
                                  labels={'value': 'Verð (ISK)', 'variable': 'Viðmið'},
                                  color_discrete_map={'Mitt_Verð': '#1f77b4', 'Keppinautar_Meðalverð': '#d62728'})
                    
                    fig.update_traces(mode='lines+markers', line=dict(width=3))
                    # Látum keppinauta línu vera stílaða aðeins öðruvísi (brotin lína stundum sniðugt en höldum solid núna)
                    fig.data[1].line.dash = 'dash'
                    fig.data[0].name = "Mitt Hótel"
                    fig.data[1].name = "Vegið Meðalverð Keppinauta"
                    
                    fig.update_yaxes(rangemode="tozero")
                    st.plotly_chart(fig, use_container_width=True)

                    st.subheader("📋 Samkeppnisvísitala (Price Index)")
                    
                    # Snyrtum framsetningu áður en við sýnum í töflu
                    df_syna = df_skyrsla.copy()
                    df_syna['Mitt Verð'] = df_syna['Mitt_Verð'].apply(lambda x: f"{int(x):,} ISK".replace(",", ".") if x > 0 else "Uppselt")
                    df_syna['Keppinautar (Vegið)'] = df_syna['Keppinautar_Meðalverð'].apply(lambda x: f"{int(x):,} ISK".replace(",", ".") if x > 0 else "Uppselt")
                    df_syna['Verðvísitala'] = df_syna['Verðvísitala (%)'].apply(lambda x: f"{x}%" if x > 0 else "-")
                    
                    st.dataframe(df_syna[['Dagsetning', 'Mitt Verð', 'Keppinautar (Vegið)', 'Verðvísitala']], use_container_width=True)
                    
                    # Bætum við snjallri ábendingu!
                    if not df_skyrsla.empty and df_skyrsla['Verðvísitala (%)'].mean() > 0:
                        medaltal_visitala = df_skyrsla[df_skyrsla['Verðvísitala (%)'] > 0]['Verðvísitala (%)'].mean()
                        if medaltal_visitala < 95:
                            st.info(f"💡 **Ábending:** Þú ert að meðaltali á **{medaltal_visitala:.1f}%** af markaðsverði. Þú gætir átt inni hækkun!")
                        elif medaltal_visitala > 105:
                            st.warning(f"💡 **Ábending:** Þú ert að meðaltali á **{medaltal_visitala:.1f}%** af markaðsverði. Þú ert talsvert dýrari en keppinautarnir.")
                        else:
                            st.success(f"💡 **Ábending:** Þú ert á **{medaltal_visitala:.1f}%** vísitölu. Þú ert algjörlega í takti við markaðinn!")

                    # ==========================================
                    # EXCEL NIÐURHAL 
                    # ==========================================
                    st.markdown("---")
                    st.subheader("📥 Sækja skýrslu")
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # FLIPI 1: Samanburður (Aðal skýrslan)
                        skyrsla_ut = df_skyrsla[['Dagsetning', 'Mitt_Verð', 'Keppinautar_Meðalverð', 'Verðvísitala (%)']].copy()
                        skyrsla_ut.rename(columns={'Mitt_Verð': 'Mitt Hótel (ISK)', 'Keppinautar_Meðalverð': 'Keppinautar Vegið (ISK)'}, inplace=True)
                        skyrsla_ut.to_excel(writer, sheet_name='Verðvísitala', index=False)
                        
                        # Búum til Excel Línurit
                        workbook = writer.book
                        worksheet = writer.sheets['Verðvísitala']
                        chart = workbook.add_chart({'type': 'line'})
                        max_row = len(skyrsla_ut)
                        
                        chart.add_series({
                            'name':       ['Verðvísitala', 0, 1], 
                            'categories': ['Verðvísitala', 1, 0, max_row, 0], 
                            'values':     ['Verðvísitala', 1, 1, max_row, 1], 
                            'line':       {'color': '#1f77b4', 'width': 2.5} 
                        })
                        chart.add_series({
                            'name':       ['Verðvísitala', 0, 2], 
                            'categories': ['Verðvísitala', 1, 0, max_row, 0], 
                            'values':     ['Verðvísitala', 1, 2, max_row, 2], 
                            'line':       {'color': '#d62728', 'width': 2.5, 'dash_type': 'dash'} 
                        })
                        chart.set_title({'name': 'Samanburður við markaðinn'})
                        worksheet.insert_chart('F2', chart)
                        
                        # FLIPI 2: Öll gögnin (Fyrir bakk-up)
                        gogn_ut = df[['Dagsetning_obj', 'Hótel', 'Fjöldi herbergja', 'Verð (ISK)', 'Staða']].copy()
                        gogn_ut.rename(columns={'Dagsetning_obj': 'Dagsetning'}, inplace=True)
                        gogn_ut['Dagsetning'] = pd.to_datetime(gogn_ut['Dagsetning']).dt.date 
                        gogn_ut.to_excel(writer, sheet_name='Öll gögn (Hrá)', index=False)
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label=f"Sækja Samanburðarskýrslu ({dagar_valdir} dagar)",
                        data=excel_data,
                        file_name=f"Samkeppnisvisitala_{datetime.date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                else:
                    st.warning("Ekkert verð fannst (Mögulega er API kvóti uppurinn eða allt uppselt).")
        else:
            st.error("Þú þarft að bæta við að minnsta kosti einum keppinauti vinstra megin áður en þú leitar!")

if athuga_lykilord():
    main()
