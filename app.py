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
                checkout = checkin + datetime.timedelta(days=1)
                
                url_api = "https://apidojo-booking-v1.p.rapidapi.com/properties/v2/get-rooms"
                qs = {"hotel_id": str(dest_id), "arrival_date": checkin.strftime("%Y-%m-%d"), 
                      "departure_date": checkout.strftime("%Y-%m-%d"), "rec_guest_qty": "2", "currency_code": "ISK"}
                res_api = requests.get(url_api, headers=headers, params=qs)
                data_api = res_api.json()
                
                if isinstance(data_api, list):
                    for room in data_api:
                        r_name = room.get("room_name", "Standard")
                        if "block" in room:
                            for b in room["block"]:
                                if "product_price_breakdown" in b:
                                    ppb = b["product_price_breakdown"]
                                    if "gross_amount" in ppb:
                                        p = ppb["gross_amount"].get("value", 0)
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
    if "mitt_hotel_flokkur" not in st.session_state: st.session_state["mitt_hotel_flokkur"] = v_stilla.get("mitt_hotel_flokkur", "Allir")
    if "keppinautar" not in st.session_state: st.session_state["keppinautar"] = v_stilla.get("keppinautar", {})

    if st.session_state["mitt_hotel_nafn"] == "":
        st.title("🏨 Velkomin(n) - Skráðu þitt hótel")
        m_nafn = st.text_input("Nafn á þínu hóteli")
        m_herb = st.number_input("Heildarfjöldi herbergja", min_value=1, value=50)
        if st.button("Vista og halda áfram", type="primary"):
            st.session_state.update({"mitt_hotel_nafn": m_nafn, "mitt_hotel_herb": m_herb})
            save_settings(m_nafn, m_herb, "Allir", st.session_state["keppinautar"])
            st.rerun()
        return 

    st.title("📊 Hótelstjórinn - Advanced Revenue System")
    st.sidebar.markdown(f"### 🏨 Mitt Hótel:\n**{st.session_state['mitt_hotel_nafn']}**\n- **Fjöldi:** {st.session_state['mitt_hotel_herb']} herb.")
    if st.sidebar.button("Breyta mínu hóteli"):
        st.session_state["mitt_hotel_nafn"] = ""; st.rerun()
    
    st.sidebar.markdown("---")
    st.sidebar.header("Bæta við Keppinauti")
    n_k = st.sidebar.text_input("Nafn á keppinauti")
    k_h = st.sidebar.number_input("Fjöldi herbergja", min_value=1, value=20)
    if st.sidebar.button("Bæta við keppinauti"):
        st.session_state['keppinautar'][n_k] = {"fjoldi": k_h}
        save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], "Allir", st.session_state['keppinautar'])
        st.rerun()

    if len(st.session_state['keppinautar']) > 0:
        st.sidebar.markdown("### Valdir keppinautar:")
        for k_hotel, k_info in st.session_state['keppinautar'].items():
            st.sidebar.markdown(f"- **{k_hotel}** ({k_info.get('fjoldi', 0)} herb.)")
        if st.sidebar.button("Hreinsa alla keppinauta"):
            st.session_state['keppinautar'] = {}; save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], "Allir", {}); st.rerun()

    c1, c2, c3 = st.columns(3)
    d = 0
    if c1.button("Sækja verð núna"): d = 1
    if c2.button("Sækja verð næstu 7 daga"): d = 7
    if c3.button("Sækja verð næstu 30 daga", type="primary"): d = 30

    if d > 0:
        leitargogn = {st.session_state['mitt_hotel_nafn']: {"fjoldi": st.session_state['mitt_hotel_herb']}}
        leitargogn.update(st.session_state['keppinautar'])
        res_df = saekja_raungogn(leitargogn, d)
        st.session_state['api_gogn'] = res_df
        st.session_state['dagar_valdir'] = d
        if not res_df.empty:
            try:
                db.append_rows(res_df.astype(str).values.tolist())
                st.toast("✅ Gögn vistuð sjálfkrafa í Pace!", icon="💾")
            except: pass

    df = st.session_state.get('api_gogn', pd.DataFrame())
    if not df.empty:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Sía herbergjaflokka")
        allir = sorted(df['Herbergjaflokkur'].unique())
        valdir = st.sidebar.multiselect("Veldu flokka:", allir, default=allir)
        df = df[df['Herbergjaflokkur'].isin(valdir)].copy()

        df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)']).astype(int)
        df['Dagsetning'] = pd.to_datetime(df['Dagsetning_obj']).dt.strftime("%d.%m")
        isl_dagar = {0:'Mán', 1:'Þri', 2:'Mið', 3:'Fim', 4:'Fös', 5:'Lau', 6:'Sun'}
        df['Vikudagur'] = pd.to_datetime(df['Dagsetning_obj']).dt.dayofweek.map(isl_dagar)
        
        # --- PIVOT TAFLA ---
        st.subheader("Verðyfirlit hlið við hlið")
        pivot = df.pivot_table(index=['Dagsetning', 'Vikudagur'], columns='Hótel', values='Verð (ISK)', aggfunc='min').reset_index()
        pivot_syna = pivot.copy()
        for col in pivot_syna.columns:
            if col not in ['Dagsetning', 'Vikudagur']:
                pivot_syna[col] = pivot_syna[col].apply(lambda x: f"{int(x):,}".replace(",", ".") + " ISK" if pd.notna(x) else "Uppselt")
        st.dataframe(pivot_syna, use_container_width=True, hide_index=True)

        # --- MEÐALVERÐ ---
        st.subheader("Meðalverð markaðar (Venjulegt vs. Vegið)")
        df_l = df[df['Verð (ISK)'] > 0]
        med_venj = df_l.groupby('Dagsetning')['Verð (ISK)'].mean().reset_index()
        df_l['Vægi'] = df_l['Verð (ISK)'] * df_l['Fjöldi herbergja']
        veg_stats = df_l.groupby('Dagsetning').agg(SV=('Vægi','sum'), SH=('Fjöldi herbergja','sum')).reset_index()
        veg_stats['Vegið'] = (veg_stats['SV'] / veg_stats['SH']).round(0).astype(int)
        saman = pd.merge(df[['Dagsetning','Vikudagur']].drop_duplicates(), med_venj, on='Dagsetning')
        saman = pd.merge(saman, veg_stats[['Dagsetning','Vegið']], on='Dagsetning')
        saman_syna = saman.copy()
        saman_syna['Verð (ISK)'] = saman_syna['Verð (ISK)'].apply(lambda x: f"{int(x):,}".replace(",", ".") + " ISK")
        saman_syna['Vegið'] = saman_syna['Vegið'].apply(lambda x: f"{int(x):,}".replace(",", ".") + " ISK")
        st.dataframe(saman_syna.rename(columns={'Verð (ISK)':'Meðalverð', 'Vegið':'Vegið meðalverð'}), use_container_width=True, hide_index=True)

        # --- VERÐÞRÓUN ---
        st.subheader("Verðþróun")
        fig = px.line(df_l, x='Dagsetning', y='Verð (ISK)', color='Hótel', line_group='Herbergjaflokkur')
        fig.add_scatter(x=saman['Dagsetning'], y=saman['Vegið'], mode='lines+markers', name='Vegið Meðalverð Markaðar', line=dict(color='black', width=3))
        st.plotly_chart(fig, use_container_width=True)

        # --- KPI ---
        st.markdown("---")
        st.subheader("⚙️ KPI & Tekjustýring")
        m_nafn = st.session_state['mitt_hotel_nafn']
        df_m = df_l[df_l['Hótel'] == m_nafn].groupby('Dagsetning')['Verð (ISK)'].mean().reset_index().rename(columns={'Verð (ISK)':'Mitt_V'})
        df_k = df_l[df_l['Hótel'] != m_nafn].copy()
        df_k['Vægi'] = df_k['Verð (ISK)'] * df_k['Fjöldi herbergja']
        k_avg = df_k.groupby('Dagsetning').agg(SV=('Vægi','sum'), SH=('Fjöldi herbergja','sum')).reset_index()
        k_avg['Markad_V'] = (k_avg['SV']/k_avg['SH']).round(0)
        kpi_base = pd.merge(df_m, k_avg[['Dagsetning','Markad_V']], on='Dagsetning', how='outer').fillna(0)
        kpi_base['Vísitala (%)'] = np.where(kpi_base['Markad_V']>0, (kpi_base['Mitt_V']/kpi_base['Markad_V']*100).round(1), 0)
        if 'Seld_herb' not in st.session_state or len(st.session_state['Seld_herb']) != len(kpi_base):
            st.session_state['Seld_herb'] = [0] * len(kpi_base)
        kpi_base['Seld herbergi'] = st.session_state['Seld_herb']
        kpi_edit = st.data_editor(kpi_base, hide_index=True, use_container_width=True)
        st.session_state['Seld_herb'] = kpi_edit['Seld herbergi'].tolist()
        kpi_edit['Nýting (%)'] = (kpi_edit['Seld herbergi'] / st.session_state['mitt_hotel_herb'] * 100).round(1)
        kpi_edit['RevPAR'] = (kpi_edit['Mitt_V'] * kpi_edit['Nýting (%)'] / 100).astype(int)
        def stefna(r):
            if r['Nýting (%)'] >= 80 and r['Vísitala (%)'] < 100: return "🔴 Hækka verð strax!"
            if r['Nýting (%)'] < 40 and r['Vísitala (%)'] > 105: return "🔵 Lækka verð"
            return "🟡 Fylgjast með"
        kpi_edit['Aðgerð'] = kpi_edit.apply(stefna, axis=1)
        st.dataframe(kpi_edit[['Dagsetning','Seld herbergi','Nýting (%)','RevPAR','Aðgerð']], use_container_width=True, hide_index=True)
        
        st.markdown("""
        **Skýringar á aðgerðum:**
        * 🔴 **Hækka verð strax!**: Nýting > 80% en þú ert ódýrari en markaðurinn.
        * 🔵 **Lækka verð**: Nýting < 40% og þú ert yfir 105% af markaðsverði.
        * 🟡 **Fylgjast með**: Staðan er í jafnvægi.
        """)

        # ==========================================
        # 🚀 RMS ÍTARLEGAR SKÝRSLUR
        # ==========================================
        st.markdown("---")
        st.header("🚀 RMS Ítarlegar Skýrslur")
        
        rms_tabs = st.tabs([
            "1. Pricing Calendar", "2. Demand vs Price", "3. Elasticity", 
            "4. Pace vs Price", "5. Competitor Shop", "6. Group Displacement", 
            "7. Opportunity", "8. Occupancy Matrix", "9. Channels", "10. AI Recs"
        ])
        
        with rms_tabs[0]:
            st.subheader("📅 Pricing Calendar (Verðdagatal)")
            st.info("Sýnir: Verð per dag, Nýtingu (OTB), Pickup og Forecast demand.")
            
        with rms_tabs[1]:
            st.subheader("📈 Demand vs Price (Demand Curve)")
            st.write("Svarar: *Hversu hátt get ég farið án þess að missa bókanir?*")
            # Fjarlægði trendline til að koma í veg fyrir hrun vegna statsmodels
            st.plotly_chart(px.scatter(kpi_edit, x="Nýting (%)", y="Mitt_V", title="Eftirspurnarferill"), use_container_width=True)
            
        with rms_tabs[2]:
            st.subheader("🧪 Price Elasticity Skýrsla")
            st.info("Hversu viðkvæmur er markaðurinn fyrir verðbreytingum?")

        with rms_tabs[3]:
            st.subheader("🏎️ Booking Pace vs Price")
            st.write("Er ég of ódýr eða of dýr?")

        with rms_tabs[4]:
            st.subheader("🕵️ Competitor Pricing (Rate Shopping)")
            st.dataframe(pivot_syna, use_container_width=True)

        with rms_tabs[5]:
            st.subheader("👥 Group Displacement Analysis")
            st.write("Á ég að taka þennan hóp eða selja herbergin dýrari stökum gestum?")

        with rms_tabs[6]:
            st.subheader("💎 Revenue Opportunity")
            st.write("Hvað gætir þú hafa selt ef þú værir ekki uppbókaður?")

        with rms_tabs[7]:
            st.subheader("🔲 Price vs Occupancy Matrix")
            st.table(pd.DataFrame({
                "Nýting": ["<30%", "30-70%", "70-90%", ">90%"],
                "Aðgerð": ["Lágmarksverð", "Fylgjast með", "Hækka verð", "Maximize"]
            }))

        with rms_tabs[8]:
            st.subheader("🌐 Channel Pricing Performance")
            st.write("Booking.com vs. Direct vs. Expedia.")

        with rms_tabs[9]:
            st.subheader("🤖 AI Pricing Recommendations")
            recs = kpi_edit[kpi_edit['Aðgerð'].str.contains('🔴|🔵')].copy()
            if not recs.empty:
                st.warning("AI Ráðleggingar fundnar!")
                st.dataframe(recs[['Dagsetning', 'Aðgerð']])
            else:
                st.success("Verðlagning er í kjörstöðu.")

        # --- EXCEL ---
        st.markdown("---")
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
            kpi_edit.to_excel(writer, sheet_name='Tekjustýring', index=False)
            pivot.to_excel(writer, sheet_name='Verðfylki (Matrix)', index=False)
            df.to_excel(writer, sheet_name='Hrá gögn', index=False)
        st.download_button("📥 Sækja Mega Excel Skýrslu", out.getvalue(), f"Report_{datetime.date.today()}.xlsx")

if athuga_lykilord(): main()
