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
        except: return None
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
    else: return True

# ==========================================
# API GAGNASÖFNUN
# ==========================================
def saekja_raungogn(hotel_dict, fjoldi_daga):
    API_KEY = "aa73991419msh780ae4bacd33dc3p12ac5fjsn494bf3cba6a6" 
    idag = datetime.date.today()
    gogn = []
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"}
    
    st.write("### 📡 Tengist við Booking.com...")
    
    for hotel, upplysingar in hotel_dict.items():
        herbergi_count = upplysingar.get("fjoldi", 20) if isinstance(upplysingar, dict) else 20
        try:
            url_loc = "https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete"
            res_loc = requests.get(url_loc, headers=headers, params={"text": hotel, "languagecode": "is"})
            data_loc = res_loc.json()
            if not data_loc: continue
            dest_id = data_loc[0].get("dest_id")
            search_type = data_loc[0].get("dest_type")
            
            for i in range(fjoldi_daga):
                checkin = idag + datetime.timedelta(days=i)
                checkout = checkin + datetime.timedelta(days=1)
                
                if search_type == "hotel":
                    url_api = "https://apidojo-booking-v1.p.rapidapi.com/properties/v2/get-rooms"
                    qs = {"hotel_id": str(dest_id), "arrival_date": checkin.strftime("%Y-%m-%d"), 
                          "departure_date": checkout.strftime("%Y-%m-%d"), "rec_guest_qty": "2", "currency_code": "ISK"}
                    res_api = requests.get(url_api, headers=headers, params=qs)
                    rooms = res_api.json()
                    if isinstance(rooms, list):
                        for r in rooms:
                            r_name = r.get("room_name", "Standard")
                            if "block" in r:
                                for b in r["block"]:
                                    if "product_price_breakdown" in b:
                                        p = b["product_price_breakdown"]["gross_amount"].get("value", 0)
                                        gogn.append({"Dagsetning_obj": checkin, "Hótel": hotel, "Herbergjaflokkur": r_name, "Verð (ISK)": int(p), "Fjöldi herbergja": herbergi_count})
        except Exception as e: st.error(f"Villa hjá {hotel}: {e}")
    return pd.DataFrame(gogn)

# ==========================================
# AÐAL FORRITIÐ
# ==========================================
def main():
    v_stilla = load_settings() or {}
    if "mitt_hotel_nafn" not in st.session_state: st.session_state["mitt_hotel_nafn"] = v_stilla.get("mitt_hotel_nafn", "")
    if "mitt_hotel_herb" not in st.session_state: st.session_state["mitt_hotel_herb"] = v_stilla.get("mitt_hotel_herb", 50)
    if "keppinautar" not in st.session_state: st.session_state["keppinautar"] = v_stilla.get("keppinautar", {})

    if st.session_state["mitt_hotel_nafn"] == "":
        st.title("🏨 Velkomin(n) - Skráðu þitt hótel")
        m_nafn = st.text_input("Nafn á þínu hóteli")
        m_herb = st.number_input("Heildarfjöldi herbergja", min_value=1, value=50)
        if st.button("Vista", type="primary"):
            st.session_state.update({"mitt_hotel_nafn": m_nafn, "mitt_hotel_herb": m_herb})
            save_settings(m_nafn, m_herb, st.session_state["keppinautar"])
            st.rerun()
        return 

    st.title("📊 Hótelstjórinn - Advanced Revenue System")
    st.sidebar.markdown(f"### 🏨 Mitt Hótel:\n**{st.session_state['mitt_hotel_nafn']}**\n- **Fjöldi:** {st.session_state['mitt_hotel_herb']} herb.")
    if st.sidebar.button("Breyta mínu hóteli"):
        st.session_state["mitt_hotel_nafn"] = ""; st.rerun()
    
    st.sidebar.header("Bæta við Keppinauti")
    n_k = st.sidebar.text_input("Nafn")
    k_h = st.sidebar.number_input("Fjöldi herb.", min_value=1, value=20)
    if st.sidebar.button("Bæta við"):
        st.session_state['keppinautar'][n_k] = {"fjoldi": k_h}
        save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], st.session_state['keppinautar'])
        st.rerun()

    if 'api_gogn' not in st.session_state: st.session_state['api_gogn'] = pd.DataFrame()
    
    c1, c2, c3 = st.columns(3)
    d = 0
    if c1.button("Sækja núna"): d = 1
    if c2.button("Sækja 7 daga"): d = 7
    if c3.button("Sækja 30 daga", type="primary"): d = 30

    if d > 0:
        l_gogn = {st.session_state['mitt_hotel_nafn']: {"fjoldi": st.session_state['mitt_hotel_herb']}}
        l_gogn.update(st.session_state['keppinautar'])
        st.session_state['api_gogn'] = saekja_raungogn(l_gogn, d)
        st.session_state['dagar_valdir'] = d
        st.session_state['vista_pessa_leit'] = True

    df = st.session_state['api_gogn']
    if not df.empty:
        st.sidebar.subheader("Sía herbergjaflokka")
        allir = sorted(df['Herbergjaflokkur'].unique())
        valdir = st.sidebar.multiselect("Veldu flokka:", allir, default=allir)
        df = df[df['Herbergjaflokkur'].isin(valdir)].copy()

        df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
        df['Dagsetning'] = pd.to_datetime(df['Dagsetning_obj']).dt.strftime("%d.%m")
        isl_dagar = {0:'Mán', 1:'Þri', 2:'Mið', 3:'Fim', 4:'Fös', 5:'Lau', 6:'Sun'}
        df['Vikudagur'] = pd.to_datetime(df['Dagsetning_obj']).dt.dayofweek.map(isl_dagar)
        
        # --- HLUTI 1: YFIRLIT ---
        st.subheader("Verðyfirlit")
        st.dataframe(df[['Dagsetning', 'Vikudagur', 'Hótel', 'Herbergjaflokkur', 'Verð (ISK)']], use_container_width=True, hide_index=True)

        # --- HLUTI 2: SAMKEPPNISVÍSITALA ---
        m_n = st.session_state['mitt_hotel_nafn']
        df_l = df[df['Verð (ISK)'] > 0].copy()
        df_m = df_l[df_l['Hótel'] == m_n].copy()
        df_k = df_l[df_l['Hótel'] != m_n].copy()

        if not df_k.empty and not df_m.empty:
            df_k['V_V'] = df_k['Verð (ISK)'] * df_k['Fjöldi herbergja']
            k_stats = df_k.groupby('Dagsetning').agg(S_V=('V_V', 'sum'), S_H=('Fjöldi herbergja', 'sum')).reset_index()
            k_stats['Kepp_Avg'] = (k_stats['S_V'] / k_stats['S_H']).round(0).astype(int)
            m_stats = df_m.groupby('Dagsetning')['Verð (ISK)'].mean().reset_index().rename(columns={'Verð (ISK)': 'Mitt_Verð'})
            m_stats['Mitt_Verð'] = m_stats['Mitt_Verð'].round(0).astype(int)
            
            df_sk = pd.merge(m_stats, k_stats[['Dagsetning', 'Kepp_Avg']], on='Dagsetning', how='outer').fillna(0)
            df_sk['Vísitala (%)'] = np.where(df_sk['Kepp_Avg']>0, (df_sk['Mitt_Verð']/df_sk['Kepp_Avg']*100).round(1), 0)
            df_sk['Mismunur'] = (df_sk['Mitt_Verð'] - df_sk['Kepp_Avg']).astype(int)

            # --- HLUTI 3: KPI EDIT ---
            st.markdown("---")
            st.subheader("⚙️ KPI & Verðstefna")
            if 'Seld_herb' not in st.session_state or len(st.session_state['Seld_herb']) != len(df_sk):
                st.session_state['Seld_herb'] = [0] * len(df_sk)
            df_sk['Seld herbergi'] = st.session_state['Seld_herb']
            kpi_edit = st.data_editor(df_sk, hide_index=True, use_container_width=True)
            st.session_state['Seld_herb'] = kpi_edit['Seld herbergi'].tolist()
            
            kpi_edit['Nýting (%)'] = (kpi_edit['Seld herbergi'] / st.session_state['mitt_hotel_herb'] * 100).round(1)
            kpi_edit['RevPAR'] = (kpi_edit['Mitt_Verð'] * kpi_edit['Nýting (%)'] / 100).round(0).astype(int)
            
            def stefna(r):
                nyt = r['Nýting (%)']
                vis = r['Vísitala (%)']
                if nyt >= 80 and vis < 100: return "🔴 Hækka verð strax!"
                if nyt >= 80: return "🟢 Sterk staða"
                if nyt < 40 and vis > 105: return "🔵 Lækka verð"
                if nyt == 0: return "⚪ Vantar gögn"
                return "🟡 Fylgjast með"
            
            kpi_edit['Aðgerð'] = kpi_edit.apply(stefna, axis=1)
            st.dataframe(kpi_edit[['Dagsetning', 'Seld herbergi', 'Nýting (%)', 'RevPAR', 'Aðgerð']], use_container_width=True, hide_index=True)

            st.markdown("""
            **Útskýringar á aðgerðum:**
            * 🔴 **Hækka verð strax!**: Nýting er yfir 80% en þú ert ódýrari en meðaltal markaðarins.
            * 🟢 **Sterk staða**: Nýting er yfir 80% og þú ert á eða yfir markaðsverði.
            * 🔵 **Lækka verð**: Nýting er undir 40% og þú ert dýrari en markaðurinn (yfir 105% vísitala).
            * 🟡 **Fylgjast með**: Nýting og verð eru í jafnvægi miðað við markaðinn.
            """)

            # --- HLUTI 4: MEGA EXCEL ---
            st.markdown("---")
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                wb = writer.book
                kpi_edit.to_excel(writer, sheet_name='Tekjustýring', index=False)
                ws = writer.sheets['Tekjustýring']
                curr = wb.add_format({'num_format': '#,##0 "ISK"'}); pct = wb.add_format({'num_format': '0.0%'})
                for i in range(len(kpi_edit)):
                    ws.write_formula(f'I{i+2}', f'=C{i+2}*H{i+2}', curr)
                ws.conditional_format(f'K2:K{len(kpi_edit)+1}', {'type':'text','criteria':'containing','value':'Hækka','format':wb.add_format({'bg_color':'#FFC7CE', 'font_color': '#9C0006'})})
                df.to_excel(writer, sheet_name='Hrá gögn', index=False)
            st.download_button("📥 Sækja Mega Excel Skýrslu", out.getvalue(), f"Revenue_Report_{datetime.date.today()}.xlsx")

if athuga_lykilord(): main()
