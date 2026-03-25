import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import requests
import io
import json
import os

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
# VISTUNAR KERFI (Fyrir herbergjafjölda og hótel)
# ==========================================
SETTINGS_FILE = "hotel_settings.json"

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def save_settings(mitt_nafn, mitt_herb, keppinautar):
    data = {
        "mitt_hotel_nafn": mitt_nafn,
        "mitt_hotel_herb": mitt_herb,
        "keppinautar": keppinautar
    }
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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
            st.error(f"Villa við að tengjast API fyrir {hotel}. (Villa: {e})")
            
    return pd.DataFrame(gogn)

# ==========================================
# AÐAL FORRITIÐ
# ==========================================
def main():
    # Hlaða inn stillingum ef þær eru til (Svo þú þurfir ekki að slá þetta inn aftur)
    if "mitt_hotel_nafn" not in st.session_state:
        vistaðar_stillingar = load_settings()
        if vistaðar_stillingar:
            st.session_state["mitt_hotel_nafn"] = vistaðar_stillingar.get("mitt_hotel_nafn", "")
            st.session_state["mitt_hotel_herb"] = vistaðar_stillingar.get("mitt_hotel_herb", 0)
            st.session_state["keppinautar"] = vistaðar_stillingar.get("keppinautar", {})
        else:
            st.session_state["mitt_hotel_nafn"] = ""
            st.session_state["mitt_hotel_herb"] = 0
            st.session_state["keppinautar"] = {}

    if st.session_state["mitt_hotel_nafn"] == "":
        st.title("🏨 Velkomin(n) - Skráðu þitt hótel")
        st.write("Byrjaðu á að skrá þitt eigið hótel. Þetta verður vistað fyrir næstu heimsókn.")
        
        m_nafn = st.text_input("Nafn á þínu hóteli")
        m_herb = st.number_input("Fjöldi herbergja á þínu hóteli", min_value=1, value=50, step=1)
        
        if st.button("Vista og halda áfram", type="primary"):
            if m_nafn:
                st.session_state["mitt_hotel_nafn"] = m_nafn
                st.session_state["mitt_hotel_herb"] = m_herb
                save_settings(m_nafn, m_herb, st.session_state["keppinautar"])
                st.rerun()
            else:
                st.warning("Þú verður að skrifa nafn á hótelinu þínu.")
        return 

    st.title("📊 Hótelstjórinn - Verðvaktin")

    # Hliðarstika fyrir Stillingar
    st.sidebar.markdown(f"### 🏨 Mitt Hótel:\n**{st.session_state['mitt_hotel_nafn']}** ({st.session_state['mitt_hotel_herb']} herb.)")
    if st.sidebar.button("Breyta mínu hóteli"):
        st.session_state["mitt_hotel_nafn"] = ""
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.header("Bæta við Keppinauti")
    
    nyr_keppinautur = st.sidebar.text_input("Nafn á keppinauti")
    kepp_herb = st.sidebar.number_input("Fjöldi herbergja (Keppinautur)", min_value=1, value=20, step=1)
    
    if st.sidebar.button("Bæta við keppinauti"):
        if nyr_keppinautur and nyr_keppinautur not in st.session_state['keppinautar']:
            if nyr_keppinautur.lower() != st.session_state['mitt_hotel_nafn'].lower():
                st.session_state['keppinautar'][nyr_keppinautur] = kepp_herb
                # Vistum nýja keppinautinn strax!
                save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], st.session_state['keppinautar'])
                st.rerun()
            else:
                st.sidebar.error("Þú getur ekki sett þitt eigið hótel sem keppinaut.")

    if len(st.session_state['keppinautar']) > 0:
        st.sidebar.markdown("### Valdir keppinautar:")
        for k_hotel, k_f in st.session_state['keppinautar'].items():
            st.sidebar.markdown(f"- **{k_hotel}** ({k_f} herb.)")
            
        if st.sidebar.button("Hreinsa alla keppinauta"):
            st.session_state['keppinautar'] = {}
            save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], {})
            st.rerun()

    # Aðal Takkarnir
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
            st.success(f"Sæki gögn fyrir þig og {len(st.session_state['keppinautar'])} keppinauta í {dagar_valdir} daga...")
            
            leitargogn = {st.session_state['mitt_hotel_nafn']: st.session_state['mitt_hotel_herb']}
            leitargogn.update(st.session_state['keppinautar'])
            
            df = saekja_raungogn(leitargogn, dagar_valdir) 

            if not df.empty:
                df['Staða'] = np.where(df['Verð (ISK)'] > 0, 'Laust', 'Uppselt')
                df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
                df['Verð sýnt'] = df['Verð (ISK)'].apply(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "")
                df['Dagsetning'] = pd.to_datetime(df['Dagsetning_obj']).dt.strftime("%d.%m")
                df.index = np.arange(1, len(df) + 1)

                df_laust = df[df['Verð (ISK)'] > 0].copy()

                # ==========================================
                # HLUTI 1: YFIRLIT YFIR ALLAN MARKAÐINN
                # ==========================================
                st.markdown("---")
                st.subheader(f"Yfirlit yfir allan markaðinn ({dagar_valdir} dagar)")
                syndir_dalkar = ['Dagsetning', 'Hótel', 'Fjöldi herbergja', 'Verð sýnt', 'Staða']
                st.dataframe(df[syndir_dalkar], use_container_width=True)

                if not df_laust.empty:
                    df_medaltal = df_laust.groupby('Dagsetning')['Verð (ISK)'].mean().reset_index()
                    df_medaltal.rename(columns={'Verð (ISK)': 'Venjulegt'}, inplace=True)

                    df_laust['Verð_Vægi'] = df_laust['Verð (ISK)'] * df_laust['Fjöldi herbergja']
                    df_veg_allir = df_laust.groupby('Dagsetning').agg(
                        Summa_Verð_Vægi=('Verð_Vægi', 'sum'),
                        Summa_Herbergi=('Fjöldi herbergja', 'sum')
                    ).reset_index()
                    df_veg_allir['Vegið'] = df_veg_allir['Summa_Verð_Vægi'] / df_veg_allir['Summa_Herbergi']

                    df_saman = pd.merge(df_medaltal, df_veg_allir[['Dagsetning', 'Vegið']], on='Dagsetning')
                    df_saman['Venjulegt'] = df_saman['Venjulegt'].round(0).astype(int)
                    df_saman['Vegið'] = df_saman['Vegið'].round(0).astype(int)

                    df_saman_syna = df_saman.copy()
                    df_saman_syna['Meðalverð'] = df_saman_syna['Venjulegt'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
                    df_saman_syna['Vegið meðalverð'] = df_saman_syna['Vegið'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
                    
                    st.subheader("Meðalverð Allra (Venjulegt vs. Vegið)")
                    st.dataframe(df_saman_syna[['Dagsetning', 'Meðalverð', 'Vegið meðalverð']], use_container_width=True)

                    st.subheader("Verðþróun Markaðarins")
                    fig1 = px.bar(df, x='Dagsetning', y='Verð (ISK)', color='Hótel', barmode='group')
                    fig1.add_scatter(x=df_saman['Dagsetning'], y=df_saman['Venjulegt'], mode='lines+markers', name='Meðalverð', line=dict(color='black', dash='dash', width=2))
                    fig1.add_scatter(x=df_saman['Dagsetning'], y=df_saman['Vegið'], mode='lines+markers', name='Vegið meðalverð', line=dict(color='red', width=3))
                    fig1.update_yaxes(rangemode="tozero")
                    st.plotly_chart(fig1, use_container_width=True)

                    # ==========================================
                    # HLUTI 2: SAMKEPPNISVÍSITALA 
                    # ==========================================
                    mitt_nafn = st.session_state['mitt_hotel_nafn']
                    df_mitt = df_laust[df_laust['Hótel'] == mitt_nafn].copy()
                    df_kepp = df_laust[df_laust['Hótel'] != mitt_nafn].copy()
                    
                    if not df_kepp.empty:
                        df_veg_kepp = df_kepp.groupby('Dagsetning').agg(
                            Summa_Verð_Vægi=('Verð_Vægi', 'sum'),
                            Summa_Herbergi=('Fjöldi herbergja', 'sum')
                        ).reset_index()
                        df_veg_kepp['Keppinautar_Meðalverð'] = (df_veg_kepp['Summa_Verð_Vægi'] / df_veg_kepp['Summa_Herbergi']).round(0).astype(int)
                    else:
                        df_veg_kepp = pd.DataFrame(columns=['Dagsetning', 'Keppinautar_Meðalverð'])
                    
                    if not df_mitt.empty:
                        df_mitt_einfalt = df_mitt[['Dagsetning', 'Verð (ISK)']].rename(columns={'Verð (ISK)': 'Mitt_Verð'})
                    else:
                        df_mitt_einfalt = pd.DataFrame(columns=['Dagsetning', 'Mitt_Verð'])

                    df_skyrsla = pd.merge(df_veg_kepp[['Dagsetning', 'Keppinautar_Meðalverð']], df_mitt_einfalt, on='Dagsetning', how='outer').fillna(0)
                    
                    df_skyrsla['Verðvísitala (%)'] = np.where(
                        (df_skyrsla['Keppinautar_Meðalverð'] > 0) & (df_skyrsla['Mitt_Verð'] > 0),
                        ((df_skyrsla['Mitt_Verð'] / df_skyrsla['Keppinautar_Meðalverð']) * 100).round(1),
                        0
                    )

                    st.markdown("---")
                    st.subheader("🎯 Samanburður: Þitt Hótel vs. Keppinautar")
                    
                    fig2 = px.line(df_skyrsla, x='Dagsetning', y=['Mitt_Verð', 'Keppinautar_Meðalverð'], 
                                  labels={'value': 'Verð (ISK)', 'variable': 'Viðmið'},
                                  color_discrete_map={'Mitt_Verð': '#1f77b4', 'Keppinautar_Meðalverð': '#d62728'})
                    
                    fig2.update_traces(mode='lines+markers', line=dict(width=3))
                    fig2.data[1].line.dash = 'dash'
                    fig2.data[0].name = "Mitt Hótel"
                    fig2.data[1].name = "Vegið Meðalverð Keppinauta"
                    fig2.update_yaxes(rangemode="tozero")
                    st.plotly_chart(fig2, use_container_width=True)

                    df_syna = df_skyrsla.copy()
                    df_syna['Mitt Verð'] = df_syna['Mitt_Verð'].apply(lambda x: f"{int(x):,} ISK".replace(",", ".") if x > 0 else "Uppselt")
                    df_syna['Keppinautar (Vegið)'] = df_syna['Keppinautar_Meðalverð'].apply(lambda x: f"{int(x):,} ISK".replace(",", ".") if x > 0 else "Uppselt")
                    df_syna['Verðvísitala'] = df_syna['Verðvísitala (%)'].apply(lambda x: f"{x}%" if x > 0 else "-")
                    
                    st.dataframe(df_syna[['Dagsetning', 'Mitt Verð', 'Keppinautar (Vegið)', 'Verðvísitala']], use_container_width=True)
                    
                    # ==========================================
                    # NÝJA OFUR-ÁBENDINGIN
                    # ==========================================
                    if not df_skyrsla.empty and df_skyrsla['Verðvísitala (%)'].mean() > 0:
                        gild_gogn = df_skyrsla[df_skyrsla['Verðvísitala (%)'] > 0]
                        medaltal_visitala = gild_gogn['Verðvísitala (%)'].mean()
                        medaltal_mitt = gild_gogn['Mitt_Verð'].mean()
                        medaltal_kepp = gild_gogn['Keppinautar_Meðalverð'].mean()
                        
                        if medaltal_visitala < 95:
                            prosent_haekkun = 100 - medaltal_visitala
                            kronu_haekkun = medaltal_kepp - medaltal_mitt
                            st.info(f"💡 **Ábending:** Þú ert að meðaltali á **{medaltal_visitala:.1f}%** af verði keppinauta. "
                                    f"Þú gætir hækkað þig um **{prosent_haekkun:.1f}%** (sem er **{int(kronu_haekkun):,} ISK**.) "
                                    f"til að ná meðalverði markaðarins sem er **{int(medaltal_kepp):,} ISK**.")
                        elif medaltal_visitala > 105:
                            prosent_laekkun = medaltal_visitala - 100
                            kronu_laekkun = medaltal_mitt - medaltal_kepp
                            st.warning(f"💡 **Ábending:** Þú ert að meðaltali á **{medaltal_visitala:.1f}%** af verði keppinauta. "
                                       f"Þú gætir þurft að lækka þig um **{prosent_laekkun:.1f}%** (sem er **{int(kronu_laekkun):,} ISK**.) "
                                       f"til að mæta meðalverði markaðarins sem er **{int(medaltal_kepp):,} ISK**.")
                        else:
                            st.success(f"💡 **Ábending:** Þú ert á **{medaltal_visitala:.1f}%** vísitölu. Frábært, þú ert algjörlega í takti við keppinautana!")

                    # ==========================================
                    # EXCEL NIÐURHAL
                    # ==========================================
                    st.markdown("---")
                    st.subheader("📥 Sækja heildarskýrslu í Excel")
                    
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        gogn_ut = df[['Dagsetning_obj', 'Hótel', 'Fjöldi herbergja', 'Verð (ISK)', 'Staða']].copy()
                        gogn_ut.rename(columns={'Dagsetning_obj': 'Dagsetning'}, inplace=True)
                        gogn_ut['Dagsetning'] = pd.to_datetime(gogn_ut['Dagsetning']).dt.date 
                        gogn_ut.to_excel(writer, sheet_name='Öll gögn (Hrá)', index=False)
                        
                        medaltal_ut = df_saman[['Dagsetning', 'Venjulegt', 'Vegið']].copy()
                        medaltal_ut.rename(columns={'Venjulegt': 'Venjulegt meðalverð', 'Vegið': 'Vegið meðalverð'}, inplace=True)
                        medaltal_ut.to_excel(writer, sheet_name='Meðalverð Allra', index=False)
                        
                        workbook = writer.book
                        worksheet1 = writer.sheets['Meðalverð Allra']
                        chart1 = workbook.add_chart({'type': 'column'})
                        max_row1 = len(medaltal_ut)
                        
                        chart1.add_series({
                            'name':       ['Meðalverð Allra', 0, 1], 
                            'categories': ['Meðalverð Allra', 1, 0, max_row1, 0], 
                            'values':     ['Meðalverð Allra', 1, 1, max_row1, 1], 
                            'fill':       {'color': '#4C78A8'} 
                        })
                        chart1.add_series({
                            'name':       ['Meðalverð Allra', 0, 2], 
                            'categories': ['Meðalverð Allra', 1, 0, max_row1, 0], 
                            'values':     ['Meðalverð Allra', 1, 2, max_row1, 2], 
                            'fill':       {'color': '#E45756'} 
                        })
                        chart1.set_title({'name': 'Meðalverð á markaðnum'})
                        chart1.set_size({'width': 720, 'height': 400})
                        worksheet1.insert_chart('E2', chart1)

                        skyrsla_ut = df_skyrsla[['Dagsetning', 'Mitt_Verð', 'Keppinautar_Meðalverð', 'Verðvísitala (%)']].copy()
                        skyrsla_ut.rename(columns={'Mitt_Verð': 'Mitt Hótel (ISK)', 'Keppinautar_Meðalverð': 'Keppinautar Vegið (ISK)'}, inplace=True)
                        skyrsla_ut.to_excel(writer, sheet_name='Verðvísitala', index=False)
                        
                        worksheet2 = writer.sheets['Verðvísitala']
                        chart2 = workbook.add_chart({'type': 'line'})
                        max_row2 = len(skyrsla_ut)
                        
                        chart2.add_series({
                            'name':       ['Verðvísitala', 0, 1], 
                            'categories': ['Verðvísitala', 1, 0, max_row2, 0], 
                            'values':     ['Verðvísitala', 1, 1, max_row2, 1], 
                            'line':       {'color': '#1f77b4', 'width': 2.5} 
                        })
                        chart2.add_series({
                            'name':       ['Verðvísitala', 0, 2], 
                            'categories': ['Verðvísitala', 1, 0, max_row2, 0], 
                            'values':     ['Verðvísitala', 1, 2, max_row2, 2], 
                            'line':       {'color': '#d62728', 'width': 2.5, 'dash_type': 'dash'} 
                        })
                        chart2.set_title({'name': 'Mitt Hótel vs. Keppinautar'})
                        chart2.set_size({'width': 720, 'height': 400})
                        worksheet2.insert_chart('F2', chart2)
                    
                    excel_data = output.getvalue()
                    
                    st.download_button(
                        label=f"Sækja Heildarskýrslu ({dagar_valdir} dagar)",
                        data=excel_data,
                        file_name=f"Hótelstjórinn_Skýrsla_{datetime.date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                else:
                    st.warning("Ekkert verð fannst.")
        else:
            st.error("Þú þarft að bæta við að minnsta kosti einum keppinauti vinstra megin áður en þú leitar!")

if athuga_lykilord():
    main()
