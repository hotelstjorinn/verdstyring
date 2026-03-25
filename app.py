import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import numpy as np
import plotly.express as px
import datetime
import requests
import io
import os

# --- TENGING VIÐ GAGNAGRUNN ---
try:
    key_dict = json.loads(st.secrets["google_credentials"])
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(key_dict, scopes=scopes)
    client = gspread.authorize(creds)
    db = client.open("Hotel_Pace_DB").sheet1
    st.sidebar.success("🟢 Tenging við gagnagrunn virk!")
except Exception as e:
    st.sidebar.error(f"🔴 Gat ekki tengst gagnagrunni: {e}")

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
# VISTUNAR KERFI
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
# API GAGNASÖFNUN (UPPFÆRT FYRIR SJÁLFVIRKA FLOKKA)
# ==========================================
def saekja_raungogn(hotel_dict, fjoldi_daga):
    API_KEY = "aa73991419msh780ae4bacd33dc3p12ac5fjsn494bf3cba6a6" 
    idag = datetime.date.today()
    gogn = []
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"
    }
    
    progress_bar = st.progress(0)
    st.write("### 📡 Sæki gögn og herbergisflokka...")
    
    total_steps = len(hotel_dict) * fjoldi_daga
    current_step = 0

    for hotel, upplysingar in hotel_dict.items():
        herbergi_count = upplysingar.get("fjoldi", 0)
        
        try:
            url_loc = "https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete"
            qs_loc = {"text": hotel, "languagecode": "is"}
            res_loc = requests.get(url_loc, headers=headers, params=qs_loc)
            data_loc = res_loc.json()
            
            if not data_loc:
                st.warning(f"❌ Booking fann ekki: '{hotel}'")
                continue
                
            dest_id = data_loc[0].get("dest_id")
            search_type = data_loc[0].get("dest_type")
            
            for i in range(fjoldi_daga):
                checkin_dagur = idag + datetime.timedelta(days=i)
                checkout_dagur = checkin_dagur + datetime.timedelta(days=1)
                
                if search_type == "hotel":
                    url_api = "https://apidojo-booking-v1.p.rapidapi.com/properties/v2/get-rooms"
                    qs_api = {
                        "hotel_id": str(dest_id),
                        "arrival_date": checkin_dagur.strftime("%Y-%m-%d"),
                        "departure_date": checkout_dagur.strftime("%Y-%m-%d"),
                        "rec_guest_qty": "2", "rec_room_qty": "1", "currency_code": "ISK"
                    }
                    res_api = requests.get(url_api, headers=headers, params=qs_api)
                    rooms_data = res_api.json()
                    
                    if isinstance(rooms_data, list):
                        for room in rooms_data:
                            room_name = room.get("room_name", "Standard")
                            if "block" in room:
                                for b in room["block"]:
                                    if "product_price_breakdown" in b:
                                        price = b["product_price_breakdown"]["gross_amount"].get("value", 0)
                                        gogn.append({
                                            "Dagsetning_obj": checkin_dagur, 
                                            "Hótel": hotel, 
                                            "Herbergjaflokkur": room_name,
                                            "Verð (ISK)": price, 
                                            "Fjöldi herbergja": herbergi_count
                                        })
                
                current_step += 1
                progress_bar.progress(min(current_step / total_steps, 1.0))

        except Exception as e:
            st.error(f"Villa hjá {hotel}: {e}")
            
    return pd.DataFrame(gogn)

# ==========================================
# AÐAL FORRITIÐ
# ==========================================
def main():
    vistaðar_stillingar = load_settings() or {}
    
    if "mitt_hotel_nafn" not in st.session_state:
        st.session_state["mitt_hotel_nafn"] = vistaðar_stillingar.get("mitt_hotel_nafn", "")
    if "mitt_hotel_herb" not in st.session_state:
        st.session_state["mitt_hotel_herb"] = vistaðar_stillingar.get("mitt_hotel_herb", 50)
    if "keppinautar" not in st.session_state:
        st.session_state["keppinautar"] = vistaðar_stillingar.get("keppinautar", {})

    if st.session_state["mitt_hotel_nafn"] == "":
        st.title("🏨 Velkomin(n) - Skráðu þitt hótel")
        m_nafn = st.text_input("Nafn á þínu hóteli")
        m_herb = st.number_input("Heildarfjöldi herbergja á hótelinu", min_value=1, value=50)
        
        if st.button("Vista og halda áfram", type="primary"):
            if m_nafn:
                st.session_state["mitt_hotel_nafn"] = m_nafn
                st.session_state["mitt_hotel_herb"] = m_herb
                save_settings(m_nafn, m_herb, st.session_state["keppinautar"])
                st.rerun()
        return 

    st.title("📊 Hótelstjórinn - Markaðsverð")

    # --- SIDEBAR ---
    st.sidebar.markdown(f"### 🏨 Mitt Hótel:\n**{st.session_state['mitt_hotel_nafn']}**\n- **Fjöldi:** {st.session_state['mitt_hotel_herb']} herb.")
    
    if st.sidebar.button("Breyta mínu hóteli"):
        st.session_state["mitt_hotel_nafn"] = ""
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.header("Bæta við Keppinauti")
    nyr_keppinautur = st.sidebar.text_input("Nafn á keppinauti")
    kepp_herb = st.sidebar.number_input("Áætlaður fjöldi herbergja", min_value=1, value=20)
    
    if st.sidebar.button("Bæta við keppinauti"):
        if nyr_keppinautur:
            st.session_state['keppinautar'][nyr_keppinautur] = {"fjoldi": kepp_herb}
            save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], st.session_state['keppinautar'])
            st.rerun()

    if len(st.session_state['keppinautar']) > 0:
        st.sidebar.markdown("### Valdir keppinautar:")
        for k_hotel, k_info in st.session_state['keppinautar'].items():
            st.sidebar.markdown(f"- **{k_hotel}** ({k_info.get('fjoldi', 0)} herb.)")
                
        if st.sidebar.button("Hreinsa alla keppinauta"):
            st.session_state['keppinautar'] = {}
            save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], {})
            st.rerun()

    # --- SÆKJA GÖGN ---
    col1, col2, col3 = st.columns(3)
    dagar = 0
    if col1.button("Sækja verð núna"): dagar = 1
    if col2.button("Sækja verð næstu 7 daga"): dagar = 7
    if col3.button("Sækja verð næstu 30 daga", type="primary"): dagar = 30

    if dagar > 0:
        leitargogn = {st.session_state['mitt_hotel_nafn']: {"fjoldi": st.session_state['mitt_hotel_herb']}}
        leitargogn.update(st.session_state['keppinautar'])
        df_raw = saekja_raungogn(leitargogn, dagar)
        st.session_state['api_gogn'] = df_raw
        st.session_state['dagar_valdir'] = dagar
        st.session_state['vista_pessa_leit'] = True

    if 'api_gogn' in st.session_state and not st.session_state['api_gogn'].empty:
        df = st.session_state['api_gogn'].copy()
        
        # --- SÍA FYRIR HERBERGJAFLOKKA ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("Sía herbergisflokka")
        allir_flokkar = sorted(df['Herbergjaflokkur'].unique())
        valdir_flokkar = st.sidebar.multiselect("Veldu flokka til að sýna:", allir_flokkar, default=allir_flokkar)
        
        df = df[df['Herbergjaflokkur'].isin(valdir_flokkar)]
        
        # Gögn vinnslu
        df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
        df['Dagsetning'] = pd.to_datetime(df['Dagsetning_obj']).dt.strftime("%d.%m")
        islenskir_dagar = {0: 'Mán', 1: 'Þri', 2: 'Mið', 3: 'Fim', 4: 'Fös', 5: 'Lau', 6: 'Sun'}
        df['Vikudagur'] = pd.to_datetime(df['Dagsetning_obj']).dt.dayofweek.map(islenskir_dagar)
        
        # Vistun í Google Sheets
        if st.session_state.get('vista_pessa_leit', False):
            try:
                db.append_rows(df.astype(str).values.tolist())
                st.toast("✅ Gögn vistuð í Sheets!", icon="💾")
                st.session_state['vista_pessa_leit'] = False
            except: pass

        # --- YFIRLITSTÖFLUR ---
        st.subheader("Markaðsyfirlit")
        st.dataframe(df[['Dagsetning', 'Vikudagur', 'Hótel', 'Herbergjaflokkur', 'Verð (ISK)']], use_container_width=True, hide_index=True)

        # Meðalverð útreikningar
        df_laust = df[df['Verð (ISK)'] > 0]
        if not df_laust.empty:
            df_medaltal = df_laust.groupby('Dagsetning')['Verð (ISK)'].mean().reset_index()
            
            st.subheader("Verðþróun")
            fig = px.line(df_laust, x='Dagsetning', y='Verð (ISK)', color='Hótel', line_group='Herbergjaflokkur', hover_data=['Herbergjaflokkur'])
            st.plotly_chart(fig, use_container_width=True)

            # --- SAMANBURÐUR (KPI) ---
            mitt_nafn = st.session_state['mitt_hotel_nafn']
            df_mitt = df_laust[df_laust['Hótel'] == mitt_nafn].groupby('Dagsetning')['Verð (ISK)'].mean().reset_index()
            df_kepp = df_laust[df_laust['Hótel'] != mitt_nafn].groupby('Dagsetning')['Verð (ISK)'].mean().reset_index()
            
            st.markdown("---")
            st.subheader("🎯 Staða gagnvart markaði (Meðaltal allra flokka)")
            
            res_kpi = pd.merge(df_mitt, df_kepp, on='Dagsetning', suffixes=('_Mitt', '_Markadur'), how='outer').fillna(0)
            res_kpi['Vísitala (%)'] = (res_kpi['Verð (ISK)_Mitt'] / res_kpi['Verð (ISK)_Markadur'] * 100).round(1)
            
            st.dataframe(res_kpi, use_container_width=True)

if athuga_lykilord():
    main()
