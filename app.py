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

def save_settings(mitt_nafn, mitt_herb, mitt_flokkur, keppinautar):
    data = {
        "mitt_hotel_nafn": mitt_nafn,
        "mitt_hotel_herb": mitt_herb,
        "mitt_hotel_flokkur": mitt_flokkur,
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
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"}
    
    st.write("### 📡 Sæki gögn frá Booking.com...")
    
    for hotel, upplysingar in hotel_dict.items():
        herbergi = upplysingar.get("fjoldi", 0)
        try:
            url_loc = "https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete"
            res_loc = requests.get(url_loc, headers=headers, params={"text": hotel, "languagecode": "is"})
            data_loc = res_loc.json()
            if not data_loc: continue
            dest_id = data_loc[0].get("dest_id")
            
            for i in range(fjoldi_daga):
                checkin = idag + datetime.timedelta(days=i)
                url_api = "https://apidojo-booking-v1.p.rapidapi.com/properties/v2/get-rooms"
                qs = {"hotel_id": str(dest_id), "arrival_date": checkin.strftime("%Y-%m-%d"), 
                      "departure_date": (checkin + datetime.timedelta(days=1)).strftime("%Y-%m-%d"), 
                      "rec_guest_qty": "2", "currency_code": "ISK"}
                res_api = requests.get(url_api, headers=headers, params=qs)
                data_api = res_api.json()
                
                if isinstance(data_api, list):
                    for room in data_api:
                        r_name = room.get("room_name", "Standard")
                        if "block" in room:
                            for b in room["block"]:
                                if "product_price_breakdown" in b:
                                    p = b["product_price_breakdown"]["gross_amount"].get("value", 0)
                                    gogn.append({
                                        "Dagsetning_obj": checkin, "Hótel": hotel, 
                                        "Herbergjaflokkur": r_name, "Verð (ISK)": int(p), 
                                        "Fjöldi herbergja": herbergi
                                    })
        except Exception as e: st.error(f"Villa hjá {hotel}: {e}")
    return pd.DataFrame(gogn)

# ==========================================
# AÐAL FORRITIÐ
# ==========================================
def main():
    v_stilla = load_settings() or {}
    if "mitt_hotel_nafn" not in st.session_state: st.session_state["mitt_hotel_nafn"] = v_stilla.get("mitt_hotel_nafn", "")
    if "mitt_hotel_herb" not in st.session_state: st.session_state["mitt_hotel_herb"] = v_stilla.get("mitt_hotel_herb", 0)
    if "keppinautar" not in st.session_state: st.session_state["keppinautar"] = v_stilla.get("keppinautar", {})

    if st.session_state["mitt_hotel_nafn"] == "":
        st.title("🏨 Velkomin(n)")
        m_nafn = st.text_input("Nafn á hóteli")
        m_herb = st.number_input("Fjöldi herbergja", min_value=1, value=50)
        if st.button("Vista", type="primary"):
            st.session_state.update({"mitt_hotel_nafn": m_nafn, "mitt_hotel_herb": m_herb})
            save_settings(m_nafn, m_herb, "Allir", st.session_state["keppinautar"])
            st.rerun()
        return 

    st.title("📊 Hótelstjórinn - Advanced Revenue System")
    
    # Sidebar
    st.sidebar.markdown(f"### 🏨 Mitt Hótel:\n**{st.session_state['mitt_hotel_nafn']}** ({st.session_state['mitt_hotel_herb']} herb.)")
    if st.sidebar.button("Breyta mínu hóteli"):
        st.session_state["mitt_hotel_nafn"] = ""; st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.header("Bæta við Keppinauti")
    n_k = st.sidebar.text_input("Nafn")
    k_h = st.sidebar.number_input("Fjöldi", min_value=1, value=20)
    if st.sidebar.button("Bæta við"):
        st.session_state['keppinautar'][n_k] = {"fjoldi": k_h}
        save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], "Allir", st.session_state['keppinautar'])
        st.rerun()

    c1, c2, c3 = st.columns(3)
    d = 0
    if c1.button("Sækja núna"): d = 1
    if c2.button("Sækja 7 daga"): d = 7
    if c3.button("Sækja 30 daga", type="primary"): d = 30

    if d > 0:
        leitargogn = {st.session_state['mitt_hotel_nafn']: {"fjoldi": st.session_state['mitt_hotel_herb']}}
        leitargogn.update(st.session_state['keppinautar'])
        res_df = saekja_raungogn(leitargogn, d)
        st.session_state['api_gogn'] = res_df
        st.session_state['dagar_valdir'] = d
        if not res_df.empty:
            try:
                db.append_rows(res_df.astype(str).values.tolist())
                st.toast("✅ Gögn vistuð sjálfvirkt í Pace!", icon="💾")
            except: pass

    df = st.session_state.get('api_gogn', pd.DataFrame())
    if not df.empty:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Sía herbergjaflokka")
        allir_fl = sorted(df['Herbergjaflokkur'].unique())
        valdir_fl = st.sidebar.multiselect("Veldu flokka:", allir_fl, default=allir_fl)
        df = df[df['Herbergjaflokkur'].isin(valdir_fl)].copy()

        df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)']).astype(int)
        df['Dagsetning'] = pd.to_datetime(df['Dagsetning_obj']).dt.strftime("%d.%m")
        isl_dagar = {0:'Mán', 1:'Þri', 2:'Mið', 3:'Fim', 4:'Fös', 5:'Lau', 6:'Sun'}
        df['Vikudagur'] = pd.to_datetime(df['Dagsetning_obj']).dt.dayofweek.map(isl_dagar)
        
        # --- TAFLA HLIÐ VIÐ HLIÐ ---
        st.subheader("Verðyfirlit hlið við hlið")
        pivot = df.pivot_table(index=['Dagsetning', 'Vikudagur'], columns='Hótel', values='Verð (ISK)', aggfunc='min').reset_index()
        pivot_syna = pivot.copy()
        for col in pivot_syna.columns:
            if col not in ['Dagsetning', 'Vikudagur']:
                pivot_syna[col] = pivot_syna[col].apply(lambda x: f"{int(x):,}".replace(",", ".") + " ISK" if pd.notna(x) else "Uppselt")
        st.dataframe(pivot_syna, use_container_width=True, hide_index=True)

        # --- AÐAL SÚLURITIÐ (VERÐÞRÓUN) ---
        st.subheader("Verðþróun")
        fig_main = px.bar(df[df['Verð (ISK)']>0], x='Dagsetning', y='Verð (ISK)', color='Hótel', barmode='group')
        st.plotly_chart(fig_main, use_container_width=True)

        # --- KPI ÚTREIKNINGAR ---
        df_l = df[df['Verð (ISK)'] > 0]
        m_nafn = st.session_state['mitt_hotel_nafn']
        df_m = df_l[df_l['Hótel'] == m_nafn].groupby('Dagsetning')['Verð (ISK)'].mean().reset_index().rename(columns={'Verð (ISK)':'Mitt_V'})
        df_k = df_l[df_l['Hótel'] != m_nafn].copy()
        df_k['Vægi'] = df_k['Verð (ISK)'] * df_k['Fjöldi herbergja']
        k_avg = df_k.groupby('Dagsetning').agg(SV=('Vægi','sum'), SH=('Fjöldi herbergja','sum')).reset_index()
        k_avg['Markad_V'] = (k_avg['SV']/k_avg['SH']).round(0).fillna(0)
        
        kpi_base = pd.merge(df_m, k_avg[['Dagsetning','Markad_V']], on='Dagsetning', how='outer').fillna(0)
        kpi_base['Vísitala (%)'] = np.where(kpi_base['Markad_V']>0, (kpi_base['Mitt_V']/kpi_base['Markad_V']*100).round(0).astype(int), 0)
        kpi_base['Verðmismunur (ISK)'] = (kpi_base['Mitt_V'] - kpi_base['Markad_V']).round(0).astype(int)

        if 'Seld_herb' not in st.session_state or len(st.session_state['Seld_herb']) != len(kpi_base):
            st.session_state['Seld_herb'] = [0] * len(kpi_base)
        kpi_base['Seld herbergi'] = st.session_state['Seld_herb']
        
        st.markdown("---")
        st.subheader("⚙️ KPI & Tekjustýring")
        kpi_edit = st.data_editor(kpi_base, hide_index=True, use_container_width=True)
        st.session_state['Seld_herb'] = kpi_edit['Seld herbergi'].tolist()
        kpi_edit['Nýting (%)'] = (kpi_edit['Seld herbergi'] / st.session_state['mitt_hotel_herb'] * 100).round(0).astype(int)
        kpi_edit['RevPAR'] = (kpi_edit['Mitt_V'] * kpi_edit['Nýting (%)'] / 100).round(0).astype(int)
        
        def stefna(r):
            if r['Nýting (%)'] >= 80 and r['Vísitala (%)'] < 100: return "🔴 Hækka verð strax!"
            if r['Nýting (%)'] < 40 and r['Vísitala (%)'] > 105: return "🔵 Lækka verð"
            return "🟡 Fylgjast með"
        kpi_edit['Aðgerð'] = kpi_edit.apply(stefna, axis=1)
        st.dataframe(kpi_edit[['Dagsetning','Seld herbergi','Nýting (%)','RevPAR','Aðgerð']], use_container_width=True, hide_index=True)

        # ==========================================
        # 🚀 RMS ÍTARLEGAR SKÝRSLUR
        # ==========================================
        st.markdown("---")
        st.header("🚀 RMS Ítarlegar Skýrslur")
        rms_tabs = st.tabs([
            "1. Pricing Calendar", "2. Demand vs Price", "3. Elasticity", 
            "4. Pace vs Price", "5. Group Displacement", "6. Revenue Opportunity", 
            "7. Channel Performance", "8. AI Recommendations"
        ])
        
        with rms_tabs[0]:
            st.subheader("📅 Pricing Calendar")
            cal_view = kpi_edit[['Dagsetning', 'Mitt_V', 'Nýting (%)', 'RevPAR']].copy()
            st.dataframe(cal_view, use_container_width=True, hide_index=True)
            
        with rms_tabs[1]:
            st.subheader("📊 Demand vs Price")
            fig_demand = px.bar(kpi_edit, x="Nýting (%)", y="Mitt_V", color="Dagsetning", title="Eftirspurn vs. Verð")
            st.plotly_chart(fig_demand, use_container_width=True)
            
        with rms_tabs[2]:
            st.subheader("🧪 Price Elasticity")
            st.line_chart(kpi_edit.set_index('Dagsetning')[['Vísitala (%)', 'Nýting (%)']])

        with rms_tabs[3]:
            st.subheader("🏎️ Booking Pace vs Price")
            st.plotly_chart(px.scatter(kpi_edit, x="Mitt_V", y="Seld herbergi", size="Nýting (%)", color="Dagsetning"), use_container_width=True)

        with rms_tabs[4]:
            st.subheader("👥 Group Displacement")
            disp = kpi_edit[['Dagsetning', 'RevPAR']].copy()
            disp['Min Group Rate'] = (disp['RevPAR'] * 1.1).round(0).astype(int)
            st.dataframe(disp, use_container_width=True, hide_index=True)

        with rms_tabs[5]:
            st.subheader("💎 Revenue Opportunity")
            opp_df = kpi_edit[['Dagsetning', 'Verðmismunur (ISK)']].copy()
            opp_df['Tækifæri'] = opp_df['Verðmismunur (ISK)'].apply(lambda x: abs(x) if x < 0 else 0).round(0).astype(int)
            st.bar_chart(opp_df.set_index('Dagsetning')['Tækifæri'])

        with rms_tabs[6]:
            st.subheader("🌐 Channel Performance")
            st.write("Áætluð ADR dreifing")
            st.table(pd.DataFrame({"Rás": ["Booking", "Expedia", "Direct"], "ADR": [(kpi_edit['Mitt_V'].mean()*0.85).astype(int), (kpi_edit['Mitt_V'].mean()*0.82).astype(int), kpi_edit['Mitt_V'].mean().astype(int)]}))

        with rms_tabs[7]:
            st.subheader("🤖 AI Recommendations")
            ai_view = kpi_edit.copy()
            ai_view['Rökstuðningur'] = np.where(ai_view['Aðgerð'].str.contains('🔴'), "Há nýting & lágt verð", "Fylgjast með markaði")
            st.dataframe(ai_view[['Dagsetning', 'Mitt_V', 'Aðgerð', 'Rökstuðningur']], use_container_width=True, hide_index=True)

        # --- EXCEL ---
        st.markdown("---")
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            kpi_edit.to_excel(writer, sheet_name='Tekjustýring', index=False)
            pivot.to_excel(writer, sheet_name='Verðfylki (Matrix)', index=False)
            df.to_excel(writer, sheet_name='Hrá gögn', index=False)
        st.download_button("📥 Sækja Mega Excel Skýrslu", out.getvalue(), f"Report_{datetime.date.today()}.xlsx")

if athuga_lykilord(): main()
