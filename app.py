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
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return None
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
# API GAGNASÖFNUN (SJÁLFVIRKIR FLOKKAR)
# ==========================================
def saekja_raungogn(hotel_dict, fjoldi_daga):
    API_KEY = "aa73991419msh780ae4bacd33dc3p12ac5fjsn494bf3cba6a6" 
    idag = datetime.date.today()
    gogn = []
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"
    }
    
    st.write("### 📡 Tengist við Booking.com...")
    
    for hotel, upplysingar in hotel_dict.items():
        # Villuvörn ef upplysingar er ekki dict (vegna gamalla gagna)
        herbergi = upplysingar.get("fjoldi", 20) if isinstance(upplysingar, dict) else 20
        
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
                                            "Fjöldi herbergja": herbergi
                                        })
                else:
                    # Fyrir svæðisleit ef við á
                    url_api = "https://apidojo-booking-v1.p.rapidapi.com/properties/list"
                    qs_api = {
                        "arrival_date": checkin_dagur.strftime("%Y-%m-%d"),
                        "departure_date": checkout_dagur.strftime("%Y-%m-%d"),
                        "guest_qty": "2", "room_qty": "1", "dest_ids": str(dest_id),
                        "search_type": search_type, "currency_code": "ISK"
                    }
                    res_api = requests.get(url_api, headers=headers, params=qs_api)
                    data_api = res_api.json()
                    if "result" in data_api and len(data_api["result"]) > 0:
                        h_data = data_api["result"][0]
                        price = h_data.get("min_total_price", 0)
                        gogn.append({
                            "Dagsetning_obj": checkin_dagur, "Hótel": hotel, 
                            "Herbergjaflokkur": "Almennt", "Verð (ISK)": price, "Fjöldi herbergja": herbergi
                        })

        except Exception as e:
            st.error(f"Villa hjá {hotel}: {e}")
            
    return pd.DataFrame(gogn)

# ==========================================
# AÐAL FORRITIÐ
# ==========================================
def main():
    # --- ÖRYGGISNET FYRIR SESSION STATE ---
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
        m_herb = st.number_input("Heildarfjöldi herbergja í þínum flokki", min_value=1, value=50)
        
        if st.button("Vista og halda áfram", type="primary"):
            if m_nafn:
                st.session_state["mitt_hotel_nafn"] = m_nafn
                st.session_state["mitt_hotel_herb"] = m_herb
                save_settings(m_nafn, m_herb, st.session_state["keppinautar"])
                st.rerun()
        return 

    st.title("📊 Hótelstjórinn - Advanced Revenue System")

    # --- SIDEBAR ---
    st.sidebar.markdown(f"### 🏨 Mitt Hótel:\n**{st.session_state['mitt_hotel_nafn']}**\n- **Fjöldi:** {st.session_state['mitt_hotel_herb']} herb.")
    
    if st.sidebar.button("Breyta mínu hóteli"):
        st.session_state["mitt_hotel_nafn"] = ""
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.header("Bæta við Keppinauti")
    nyr_keppinautur = st.sidebar.text_input("Nafn á keppinauti")
    kepp_herb = st.sidebar.number_input("Fjöldi herbergja hjá keppinauti", min_value=1, value=20)
    
    if st.sidebar.button("Bæta við keppinauti"):
        if nyr_keppinautur:
            st.session_state['keppinautar'][nyr_keppinautur] = {"fjoldi": kepp_herb}
            save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], st.session_state['keppinautar'])
            st.rerun()

    if len(st.session_state['keppinautar']) > 0:
        st.sidebar.markdown("### Valdir keppinautar:")
        for k_hotel, k_info in st.session_state['keppinautar'].items():
            f_count = k_info.get('fjoldi', 0) if isinstance(k_info, dict) else "N/A"
            st.sidebar.markdown(f"- **{k_hotel}** ({f_count} herb.)")
                
        if st.sidebar.button("Hreinsa alla keppinauta"):
            st.session_state['keppinautar'] = {}
            save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], {})
            st.rerun()

    # --- SÆKJA GÖGN ---
    if 'api_gogn' not in st.session_state:
        st.session_state['api_gogn'] = pd.DataFrame()
        st.session_state['dagar_valdir'] = 0

    col1, col2, col3 = st.columns(3)
    dagar_val = 0
    if col1.button("Sækja verð núna"): dagar_val = 1
    if col2.button("Sækja verð næstu 7 daga"): dagar_val = 7
    if col3.button("Sækja verð næstu 30 daga", type="primary"): dagar_val = 30

    if dagar_val > 0:
        leitargogn = {st.session_state['mitt_hotel_nafn']: {"fjoldi": st.session_state['mitt_hotel_herb']}}
        leitargogn.update(st.session_state['keppinautar'])
        df_new = saekja_raungogn(leitargogn, dagar_val)
        st.session_state['api_gogn'] = df_new
        st.session_state['dagar_valdir'] = dagar_val
        st.session_state['vista_pessa_leit'] = True

    df = st.session_state['api_gogn']
    
    if not df.empty:
        # --- SÍA FYRIR HERBERGJAFLOKKA ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("Sía herbergisflokka")
        allir_flokkar = sorted(df['Herbergjaflokkur'].unique())
        valdir_flokkar = st.sidebar.multiselect("Veldu flokka til að greina:", allir_flokkar, default=allir_flokkar)
        
        df = df[df['Herbergjaflokkur'].isin(valdir_flokkar)].copy()
        
        df['Staða'] = np.where(df['Verð (ISK)'] > 0, 'Laust', 'Uppselt')
        df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
        df['Verð sýnt'] = df['Verð (ISK)'].apply(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "")
        df['Dagsetning'] = pd.to_datetime(df['Dagsetning_obj']).dt.strftime("%d.%m")
        islenskir_dagar = {0: 'Mán', 1: 'Þri', 2: 'Mið', 3: 'Fim', 4: 'Fös', 5: 'Lau', 6: 'Sun'}
        df['Vikudagur'] = pd.to_datetime(df['Dagsetning_obj']).dt.dayofweek.map(islenskir_dagar)
        
        df_laust = df[df['Verð (ISK)'] > 0].copy()

        # --- SJÁLFKRAFA VISTUN Í GOOGLE SHEETS ---
        if st.session_state.get('vista_pessa_leit', False):
            try:
                nuna = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df_save = df.copy()
                df_save["Sótt klukkan"] = nuna
                df_save["Dagsetning_obj"] = df_save["Dagsetning_obj"].astype(str)
                db.append_rows(df_save.values.tolist())
                st.toast("✅ Ný gögn vistuð í gagnagrunn!", icon="💾")
                st.session_state['vista_pessa_leit'] = False
            except Exception as e:
                st.error(f"Villa við vistun: {e}")

        # ==========================================
        # HLUTI 1: VERÐYFIRLIT
        # ==========================================
        st.markdown("---")
        st.subheader(f"Verðyfirlit ({st.session_state['dagar_valdir']} dagar)")
        st.dataframe(df[['Dagsetning', 'Vikudagur', 'Hótel', 'Herbergjaflokkur', 'Verð sýnt', 'Staða']], use_container_width=True, hide_index=True)

        if not df_laust.empty:
            # Útreikningar fyrir meðalverð
            df_medaltal = df_laust.groupby('Dagsetning')['Verð (ISK)'].mean().reset_index()
            df_medaltal.rename(columns={'Verð (ISK)': 'Venjulegt'}, inplace=True)
            
            df_laust['Verð_Vægi'] = df_laust['Verð (ISK)'] * df_laust['Fjöldi herbergja']
            df_veg = df_laust.groupby('Dagsetning').agg(S_V=('Verð_Vægi', 'sum'), S_H=('Fjöldi herbergja', 'sum')).reset_index()
            df_veg['Vegið'] = (df_veg['S_V'] / df_veg['S_H']).round(0)
            
            df_saman = pd.merge(df_medaltal, df_veg[['Dagsetning', 'Vegið']], on='Dagsetning')
            
            st.subheader("Verðþróun")
            fig1 = px.bar(df_laust, x='Dagsetning', y='Verð (ISK)', color='Hótel', barmode='group')
            fig1.add_scatter(x=df_saman['Dagsetning'], y=df_saman['Vegið'], mode='lines+markers', name='Vegið Meðalverð', line=dict(color='red', width=3))
            st.plotly_chart(fig1, use_container_width=True)

        # ==========================================
        # HLUTI 2: SAMKEPPNISVÍSITALA
        # ==========================================
        mitt_nafn = st.session_state['mitt_hotel_nafn']
        df_mitt = df_laust[df_laust['Hótel'] == mitt_nafn].copy()
        df_kepp = df_laust[df_laust['Hótel'] != mitt_nafn].copy()
        
        if not df_kepp.empty and not df_mitt.empty:
            # Vegið meðalverð keppinauta
            df_kepp['V_V'] = df_kepp['Verð (ISK)'] * df_kepp['Fjöldi herbergja']
            kepp_stats = df_kepp.groupby('Dagsetning').agg(S_V=('V_V', 'sum'), S_H=('Fjöldi herbergja', 'sum')).reset_index()
            kepp_stats['Kepp_Avg'] = (kepp_stats['S_V'] / kepp_stats['S_H']).round(0)
            
            mitt_stats = df_mitt.groupby('Dagsetning')['Verð (ISK)'].mean().reset_index().rename(columns={'Verð (ISK)': 'Mitt_Verð'})
            
            df_skyrsla = pd.merge(mitt_stats, kepp_stats[['Dagsetning', 'Kepp_Avg']], on='Dagsetning', how='outer').fillna(0)
            df_skyrsla['Vísitala (%)'] = np.where(df_skyrsla['Kepp_Avg']>0, (df_skyrsla['Mitt_Verð']/df_skyrsla['Kepp_Avg']*100).round(1), 0)
            
            st.subheader("🎯 Samanburður: Mitt Hótel vs. Keppinautar")
            fig2 = px.line(df_skyrsla, x='Dagsetning', y=['Mitt_Verð', 'Kepp_Avg'], labels={'value':'ISK', 'variable':'Hótel'})
            st.plotly_chart(fig2, use_container_width=True)

            # ==========================================
            # HLUTI 3: KPI & VERÐSTEFNA
            # ==========================================
            st.markdown("---")
            st.subheader("⚙️ Tekjustýring & KPI")
            
            if 'Seld_herb' not in st.session_state or len(st.session_state['Seld_herb']) != len(df_skyrsla):
                st.session_state['Seld_herb'] = [0] * len(df_skyrsla)
                
            kpi_data = df_skyrsla.copy()
            kpi_data['Seld herbergi'] = st.session_state['Seld_herb']
            
            kpi_edit = st.data_editor(kpi_data, hide_index=True, use_container_width=True)
            st.session_state['Seld_herb'] = kpi_edit['Seld herbergi'].tolist()
            
            # Útreikningar fyrir lokatöflu
            kpi_edit['Nýting (%)'] = (kpi_edit['Seld herbergi'] / st.session_state['mitt_hotel_herb'] * 100).round(1)
            kpi_edit['RevPAR'] = (kpi_edit['Mitt_Verð'] * kpi_edit['Nýting (%)'] / 100).astype(int)
            
            def gera_stefnu(row):
                nyt = row['Nýting (%)']
                vis = row['Vísitala (%)']
                if nyt >= 80 and vis < 100: return "🔴 Hækka verð strax!"
                if nyt >= 80 and vis >= 100: return "🟢 Sterk staða"
                if nyt < 40 and vis > 105: return "🔵 Lækka verð"
                return "🟡 Fylgjast með"

            kpi_edit['Aðgerð'] = kpi_edit.apply(gera_stefnu, axis=1)
            st.dataframe(kpi_edit[['Dagsetning', 'Seld herbergi', 'Nýting (%)', 'RevPAR', 'Aðgerð']], use_container_width=True, hide_index=True)

            # ==========================================
            # HLUTI 4: EXCEL SKÝRSLA
            # ==========================================
            st.markdown("---")
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                kpi_edit.to_excel(writer, sheet_name='Tekjustýring', index=False)
                df.to_excel(writer, sheet_name='Hrá gögn', index=False)
            
            st.download_button(label="📥 Sækja Mega Excel Skýrslu", data=output.getvalue(), 
                               file_name=f"Revenue_Report_{datetime.date.today()}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if athuga_lykilord():
    main()
