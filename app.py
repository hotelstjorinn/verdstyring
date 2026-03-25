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
# ------------------------------

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
    
    st.write("### 📡 Tengist við Booking.com...")
    
    for hotel, herbergi in hotel_dict.items():
        try:
            url_loc = "https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete"
            qs_loc = {"text": hotel, "languagecode": "is"}
            res_loc = requests.get(url_loc, headers=headers, params=qs_loc)
            data_loc = res_loc.json()
            
            if not data_loc or len(data_loc) == 0:
                st.warning(f"❌ Booking fann ekki gististaðinn: '{hotel}'")
                continue
                
            dest_id = data_loc[0].get("dest_id")
            search_type = data_loc[0].get("dest_type", "city") 
            fundid_nafn = data_loc[0].get("name", hotel)
            st.info(f"📍 **{hotel}** fundið! Booking Nafn: *{fundid_nafn}* | Booking ID: `{dest_id}`")
            
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
                        "rec_guest_qty": "2", "rec_room_qty": "1", "currency_code": "ISK"
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
                        if verd_listi: verd = min(verd_listi) 
                else:
                    url_api = "https://apidojo-booking-v1.p.rapidapi.com/properties/list"
                    qs_api = {
                        "offset": "0", "arrival_date": checkin_dagur.strftime("%Y-%m-%d"),
                        "departure_date": checkout_dagur.strftime("%Y-%m-%d"),
                        "guest_qty": "2", "room_qty": "1", "dest_ids": str(dest_id),  
                        "search_type": search_type, "price_filter_currencycode": "ISK", "children_qty": "0"
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

                gogn.append({"Dagsetning_obj": checkin_dagur, "Hótel": hotel, "Verð (ISK)": verd, "Fjöldi herbergja": herbergi})
        except Exception as e:
            st.error(f"Villa við að tengjast API fyrir {hotel}. (Villa: {e})")
    return pd.DataFrame(gogn)

# ==========================================
# AÐAL FORRITIÐ
# ==========================================
def main():
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
        m_nafn = st.text_input("Nafn á þínu hóteli")
        m_herb = st.number_input("Fjöldi herbergja á þínu hóteli", min_value=1, value=50, step=1)
        if st.button("Vista og halda áfram", type="primary"):
            if m_nafn:
                st.session_state["mitt_hotel_nafn"] = m_nafn
                st.session_state["mitt_hotel_herb"] = m_herb
                save_settings(m_nafn, m_herb, st.session_state["keppinautar"])
                st.rerun()
        return 

    st.title("📊 Hótelstjórinn - Advanced Revenue System")

    st.sidebar.markdown(f"### 🏨 Mitt Hótel:\n**{st.session_state['mitt_hotel_nafn']}** ({st.session_state['mitt_hotel_herb']} herb.)")
    if st.sidebar.button("Breyta mínu hóteli"):
        st.session_state["mitt_hotel_nafn"] = ""
        st.rerun()
        
    st.sidebar.markdown("---")
    st.sidebar.header("Bæta við Keppinauti")
    nyr_keppinautur = st.sidebar.text_input("Nafn á keppinauti")
    kepp_herb = st.sidebar.number_input("Fjöldi herbergja (Keppinautur)", min_value=1, value=20, step=1)
    
    if st.sidebar.button("Bæta við keppinauti"):
        if nyr_keppinautur and nyr_keppinautur not in st.session_state['keppinautar'] and nyr_keppinautur.lower() != st.session_state['mitt_hotel_nafn'].lower():
            st.session_state['keppinautar'][nyr_keppinautur] = kepp_herb
            save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], st.session_state['keppinautar'])
            st.rerun()

    if len(st.session_state['keppinautar']) > 0:
        st.sidebar.markdown("### Valdir keppinautar:")
        for k_hotel, k_f in st.session_state['keppinautar'].items():
            st.sidebar.markdown(f"- **{k_hotel}** ({k_f} herb.)")
        if st.sidebar.button("Hreinsa alla keppinauta"):
            st.session_state['keppinautar'] = {}
            save_settings(st.session_state['mitt_hotel_nafn'], st.session_state['mitt_hotel_herb'], {})
            st.rerun()

    if 'api_gogn' not in st.session_state:
        st.session_state['api_gogn'] = pd.DataFrame()
        st.session_state['dagar_valdir'] = 0

    col1, col2, col3 = st.columns(3)
    if col1.button("Sækja verð núna"): st.session_state['dagar_valdir'] = 1
    if col2.button("Sækja verð næstu 7 daga"): st.session_state['dagar_valdir'] = 7
    if col3.button("Sækja verð næstu 30 daga", type="primary"): st.session_state['dagar_valdir'] = 30

    # NÝR KÓÐI FYRIR SJÁLFVIRKNI: Við setjum upp "fána" ef ný leit var framkvæmd
    if st.session_state['dagar_valdir'] > 0 and st.session_state.get('síðast_leitað') != st.session_state['dagar_valdir']:
        if len(st.session_state['keppinautar']) > 0:
            leitargogn = {st.session_state['mitt_hotel_nafn']: st.session_state['mitt_hotel_herb']}
            leitargogn.update(st.session_state['keppinautar'])
            df = saekja_raungogn(leitargogn, st.session_state['dagar_valdir']) 
            st.session_state['api_gogn'] = df
            st.session_state['síðast_leitað'] = st.session_state['dagar_valdir']
            st.session_state['vista_pessa_leit'] = True  # <--- Hér fer fáninn upp!

    df = st.session_state['api_gogn']
    
    if not df.empty:
        df['Staða'] = np.where(df['Verð (ISK)'] > 0, 'Laust', 'Uppselt')
        df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
        df['Verð sýnt'] = df['Verð (ISK)'].apply(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "")
        df['Dagsetning'] = pd.to_datetime(df['Dagsetning_obj']).dt.strftime("%d.%m")
        
        islenskir_dagar = {0: 'Mán', 1: 'Þri', 2: 'Mið', 3: 'Fim', 4: 'Fös', 5: 'Lau', 6: 'Sun'}
        df['Vikudagur'] = pd.to_datetime(df['Dagsetning_obj']).dt.dayofweek.map(islenskir_dagar)
        
        df_laust = df[df['Verð (ISK)'] > 0].copy()

        # --- SJÁLFKRAFA VISTUN (Ef fáninn er uppi) ---
        if st.session_state.get('vista_pessa_leit', False):
            try:
                nuna = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                df_til_ad_vista = df.copy() 
                df_til_ad_vista["Sótt klukkan"] = nuna
                df_til_ad_vista["Dagsetning_obj"] = df_til_ad_vista["Dagsetning_obj"].astype(str)
                dalkar = ["Sótt klukkan", "Dagsetning_obj", "Dagsetning", "Vikudagur", "Hótel", "Fjöldi herbergja", "Verð (ISK)", "Staða"]
                df_til_ad_vista = df_til_ad_vista[dalkar]

                gogn_til_ad_vista = df_til_ad_vista.values.tolist()
                db.append_rows(gogn_til_ad_vista)
                # Toast er lítil tilkynning sem poppar upp í nokkrar sekúndur án þess að taka pláss
                st.toast("✅ Ný gögn vistuð sjálfkrafa í gagnagrunn!", icon="💾") 
            except Exception as e:
                st.error(f"🔴 Eitthvað fór úrskeiðis við sjálfvirka vistun: {e}")
            
            # Tökum fánann niður, svo forritið visti ekki aftur nema gerð sé ný leit!
            st.session_state['vista_pessa_leit'] = False 
        # ---------------------------------------------

        # ==========================================
        # HLUTI 1: YFIRLIT ALLRA 
        # ==========================================
        st.markdown("---")
        st.subheader(f"Verðyfirlit ({st.session_state['dagar_valdir']} dagar)")
        
        syndir_dalkar = ['Dagsetning', 'Vikudagur', 'Hótel', 'Fjöldi herbergja', 'Verð sýnt', 'Staða']
        st.dataframe(df[syndir_dalkar], use_container_width=True)

        st.subheader(f"Verðyfirlit hlið við hlið ({st.session_state['dagar_valdir']} dagar)")
        if not df_laust.empty:
            df_pivot = df_laust.pivot_table(index=['Dagsetning', 'Vikudagur'], columns='Hótel', values='Verð (ISK)', aggfunc='first').reset_index()
            for col in df_pivot.columns:
                if col not in ['Dagsetning', 'Vikudagur']:
                    df_pivot[col] = df_pivot[col].apply(lambda x: f"{int(x):,} ISK".replace(",", ".") if pd.notna(x) and x > 0 else "Uppselt")
            st.dataframe(df_pivot, use_container_width=True, hide_index=True)

        if not df_laust.empty:
            df_medaltal = df_laust.groupby('Dagsetning')['Verð (ISK)'].mean().reset_index()
            df_medaltal.rename(columns={'Verð (ISK)': 'Venjulegt'}, inplace=True)

            df_laust['Verð_Vægi_Allir'] = df_laust['Verð (ISK)'] * df_laust['Fjöldi herbergja']
            df_veg_allir = df_laust.groupby('Dagsetning').agg(
                Summa_Verð_Vægi=('Verð_Vægi_Allir', 'sum'),
                Summa_Herbergi=('Fjöldi herbergja', 'sum')
            ).reset_index()
            df_veg_allir['Vegið'] = df_veg_allir['Summa_Verð_Vægi'] / df_veg_allir['Summa_Herbergi']

            df_saman = pd.merge(df_medaltal, df_veg_allir[['Dagsetning', 'Vegið']], on='Dagsetning')
            df_dag = df[['Dagsetning', 'Vikudagur']].drop_duplicates()
            df_saman = pd.merge(df_dag, df_saman, on='Dagsetning')
            
            df_saman['Venjulegt'] = df_saman['Venjulegt'].round(0).astype(int)
            df_saman['Vegið'] = df_saman['Vegið'].round(0).astype(int)

            df_saman_syna = df_saman.copy()
            df_saman_syna['Meðalverð'] = df_saman_syna['Venjulegt'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
            df_saman_syna['Vegið meðalverð'] = df_saman_syna['Vegið'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
            
            st.subheader("Meðalverð markaðar (Venjulegt vs. Vegið)")
            st.dataframe(df_saman_syna[['Dagsetning', 'Vikudagur', 'Meðalverð', 'Vegið meðalverð']], use_container_width=True, hide_index=True)

            st.subheader("Verðþróun")
            fig1 = px.bar(df, x='Dagsetning', y='Verð (ISK)', color='Hótel', barmode='group', hover_data=['Vikudagur'])
            fig1.add_scatter(x=df_saman['Dagsetning'], y=df_saman['Venjulegt'], mode='lines+markers', name='Meðalverð', line=dict(color='black', dash='dash', width=2))
            fig1.add_scatter(x=df_saman['Dagsetning'], y=df_saman['Vegið'], mode='lines+markers', name='Vegið meðalverð', line=dict(color='red', width=3))
            fig1.update_yaxes(rangemode="tozero")
            st.plotly_chart(fig1, use_container_width=True)

        # ==========================================
        # HLUTI 2: SAMKEPPNISVÍSITALA
        # ==========================================
        if not df_laust.empty:
            mitt_nafn = st.session_state['mitt_hotel_nafn']
            df_mitt = df_laust[df_laust['Hótel'] == mitt_nafn].copy()
            df_kepp = df_laust[df_laust['Hótel'] != mitt_nafn].copy()
            
            if not df_kepp.empty:
                df_kepp['Verð_Vægi'] = df_kepp['Verð (ISK)'] * df_kepp['Fjöldi herbergja']
                df_veg_kepp = df_kepp.groupby('Dagsetning').agg(
                    Summa_Verð_Vægi=('Verð_Vægi', 'sum'), Summa_Herbergi=('Fjöldi herbergja', 'sum')
                ).reset_index()
                df_veg_kepp['Keppinautar_Meðalverð'] = (df_veg_kepp['Summa_Verð_Vægi'] / df_veg_kepp['Summa_Herbergi']).round(0).astype(int)
            else:
                df_veg_kepp = pd.DataFrame(columns=['Dagsetning', 'Keppinautar_Meðalverð'])
            
            if not df_mitt.empty:
                df_mitt_einfalt = df_mitt[['Dagsetning', 'Verð (ISK)']].rename(columns={'Verð (ISK)': 'Mitt_Verð'})
            else:
                df_mitt_einfalt = pd.DataFrame(columns=['Dagsetning', 'Mitt_Verð'])

            df_skyrsla = pd.merge(df_veg_kepp[['Dagsetning', 'Keppinautar_Meðalverð']], df_mitt_einfalt, on='Dagsetning', how='outer').fillna(0)
            df_skyrsla = pd.merge(df_dag, df_skyrsla, on='Dagsetning') 
            df_skyrsla['Verðvísitala (%)'] = np.where(
                (df_skyrsla['Keppinautar_Meðalverð'] > 0) & (df_skyrsla['Mitt_Verð'] > 0),
                ((df_skyrsla['Mitt_Verð'] / df_skyrsla['Keppinautar_Meðalverð']) * 100).round(1), 0
            )
            df_skyrsla['Verðmismunur (ISK)'] = df_skyrsla['Mitt_Verð'] - df_skyrsla['Keppinautar_Meðalverð']

            st.markdown("---")
            st.subheader("🎯 Samanburður: Þitt Hótel vs. Meðalverð Keppinauta")
            
            fig2 = px.line(df_skyrsla, x='Dagsetning', y=['Mitt_Verð', 'Keppinautar_Meðalverð'], 
                          labels={'value': 'Verð (ISK)', 'variable': 'Viðmið'},
                          color_discrete_map={'Mitt_Verð': '#1f77b4', 'Keppinautar_Meðalverð': '#d62728'})
            fig2.update_traces(mode='lines+markers', line=dict(width=3))
            fig2.data[1].line.dash = 'dash'
            fig2.data[0].name = "Mitt Hótel"
            fig2.data[1].name = "Vegið Meðalverð Keppinauta"
            fig2.update_yaxes(rangemode="tozero")
            st.plotly_chart(fig2, use_container_width=True)
            
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
            # HLUTI 3: KPI REIKNIVÉL & VERÐSTEFNA
            # ==========================================
            st.markdown("---")
            st.subheader("⚙️ KPI & Tekjustýring (Sláðu inn seld herbergi)")

            df_kpi = df_skyrsla[['Dagsetning', 'Vikudagur', 'Mitt_Verð', 'Keppinautar_Meðalverð', 'Verðmismunur (ISK)', 'Verðvísitala (%)']].copy()
            if 'Seld_herb' not in st.session_state:
                st.session_state['Seld_herb'] = [0] * len(df_kpi)
            
            df_kpi['Seld herbergi'] = st.session_state['Seld_herb'][:len(df_kpi)] 
            
            kpi_editable = st.data_editor(
                df_kpi,
                column_config={
                    "Seld herbergi": st.column_config.NumberColumn(
                        "🛏️ Seld herbergi (Sláðu inn)", min_value=0, max_value=st.session_state['mitt_hotel_herb'], step=1
                    ),
                    "Mitt_Verð": st.column_config.NumberColumn("ADR (Þitt Verð)", format="%d ISK"),
                    "Keppinautar_Meðalverð": st.column_config.NumberColumn("Markaðsverð", format="%d ISK"),
                    "Verðmismunur (ISK)": st.column_config.NumberColumn("Mismunur (ISK)", format="%d ISK")
                },
                disabled=["Dagsetning", "Vikudagur", "Mitt_Verð", "Keppinautar_Meðalverð", "Verðmismunur (ISK)", "Verðvísitala (%)"],
                hide_index=True,
                use_container_width=True
            )

            st.session_state['Seld_herb'] = kpi_editable['Seld herbergi'].tolist()

            kpi_editable['Nýting (%)'] = ((kpi_editable['Seld herbergi'] / st.session_state['mitt_hotel_herb']) * 100).round(1)
            kpi_editable['RevPAR (ISK)'] = (kpi_editable['Mitt_Verð'] * (kpi_editable['Nýting (%)'] / 100)).round(0).astype(int)
            kpi_editable['Heildartekjur (ISK)'] = (kpi_editable['Seld herbergi'] * kpi_editable['Mitt_Verð']).astype(int)

            def reikna_stefnu(row):
                nyt = row['Nýting (%)']
                visitala = row['Verðvísitala (%)']
                if nyt == 0: return "❔ Vantar gögn (Seld herb)"
                if nyt >= 80 and visitala < 100: return "🔴 Hækka verð strax!"
                if nyt >= 80 and visitala >= 100: return "🟢 Sterk staða - Halda verði"
                if nyt < 40 and visitala > 105: return "🔵 Lækka verð / Búa til tilboð"
                if nyt < 40 and visitala <= 100: return "🟡 Ódýr, en engin sala."
                return "🟡 Fylgjast með markaði"

            kpi_editable['Verðstefna (Aðgerð)'] = kpi_editable.apply(reikna_stefnu, axis=1)

            st.markdown("#### Útreiknuð Staða & Verðstefna")
            synd_kpi = kpi_editable[['Dagsetning', 'Vikudagur', 'Seld herbergi', 'Nýting (%)', 'Heildartekjur (ISK)', 'RevPAR (ISK)', 'Verðstefna (Aðgerð)']].copy()
            synd_kpi['RevPAR (ISK)'] = synd_kpi['RevPAR (ISK)'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
            synd_kpi['Heildartekjur (ISK)'] = synd_kpi['Heildartekjur (ISK)'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
            st.dataframe(synd_kpi, use_container_width=True, hide_index=True)

            st.markdown("""
            **Hvernig hugsar Verðstefnan?**
            * 🔴 **Hækka verð strax!** (Nýting komin yfir 80% EN þú ert ódýrari en markaðurinn).
              * *Hugsunin:* Hótelið þitt er að fyllast, sennilega af því að þú ert ódýrastur. Markaðurinn þolir hærra verð, svo þú átt að hækka þitt verð strax á síðustu herbergjunum til að græða meira á þeim (hámarka ADR/RevPAR).
            * 🟢 **Sterk staða - Halda verði** (Nýting yfir 80% OG þú ert dýrari en markaðurinn).
              * *Hugsunin:* Þú ert að ná að fylla hótelið þótt þú sért á hærra verði en hinir. Frábært starf! Ekki breyta neinu.
            * 🔵 **Lækka verð / Búa til tilboð** (Nýting undir 40% OG þú ert dýrari en markaðurinn).
              * *Hugsunin:* Það er lítið að gera hjá þér og gestirnir eru frekar að bóka hjá keppinautunum af því að þeir eru ódýrari. Þú þarft að lækka verðið (eða setja upp Flash Deal) til að stela bókunum til baka.
            * 🟡 **Ódýr, en engin sala.** (Nýting undir 40% EN þú ert samt ódýrari en markaðurinn).
              * *Hugsunin:* Það er dautt yfir öllu. Þótt þú sért ódýrastur er enginn að bóka. Að lækka verðið enn meira mun líklega ekki virka (eftirspurnin er bara ekki til staðar). Betra er að reyna að lokka fólk með aukaverðmætum (t.d. "Frír morgunmatur" eða "Late check-out") frekar en að rústa verðstefnunni þinni.
            * 🟡 **Fylgjast með markaði** (Allt þar á milli).
              * *Hugsunin:* Nýting er venjuleg (40-79%). Bókanir eru að rúlla inn á eðlilegum hraða. Bara leyfa þessu að malla og fylgjast með.
            """)

            # ==========================================
            # HLUTI 4: EXCEL NIÐURHAL (LIFANDI OG LAGAÐ FYRIR LIBREOFFICE)
            # ==========================================
            st.markdown("---")
            st.subheader("📥 Sækja Mega Excel Skýrslu (LIFANDI!)")
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                workbook = writer.book
                
                kpi_ut = kpi_editable[['Dagsetning', 'Vikudagur', 'Seld herbergi']].copy()
                kpi_ut['Nýting (%)'] = ""
                kpi_ut['ADR (Mitt Verð)'] = kpi_editable['Mitt_Verð']
                kpi_ut['Markaðsverð'] = kpi_editable['Keppinautar_Meðalverð']
                kpi_ut['Verðmismunur (ISK)'] = ""
                kpi_ut['Verðvísitala (%)'] = ""
                kpi_ut['RevPAR (ISK)'] = ""
                kpi_ut['Heildartekjur (ISK)'] = ""
                kpi_ut['Verðstefna (Aðgerð)'] = "" 

                kpi_ut.to_excel(writer, sheet_name='Tekjustýring (KPI)', index=False)
                worksheet_kpi = writer.sheets['Tekjustýring (KPI)']

                pct_format = workbook.add_format({'num_format': '0.0%'})
                currency_format = workbook.add_format({'num_format': '#,##0 "ISK"'})
                bold_format = workbook.add_format({'bold': True})
                
                format_green = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
                format_red = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
                format_yellow = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})

                num_rows = len(kpi_ut)
                mitt_herb = st.session_state['mitt_hotel_herb']
                
                for i in range(num_rows):
                    row = i + 2 
                    seld = kpi_editable.iloc[i]['Seld herbergi']
                    adr = kpi_editable.iloc[i]['Mitt_Verð']
                    markad = kpi_editable.iloc[i]['Keppinautar_Meðalverð']
                    
                    n_val = seld / mitt_herb if mitt_herb > 0 else 0
                    m_val = adr - markad
                    v_val = adr / markad if markad > 0 else 0
                    r_val = adr * n_val
                    t_val = seld * adr
                    s_val = kpi_editable.iloc[i]['Verðstefna (Aðgerð)']

                    worksheet_kpi.write_formula(f'D{row}', f'=C{row}/{mitt_herb}', pct_format, value=n_val)
                    worksheet_kpi.write_formula(f'G{row}', f'=E{row}-F{row}', currency_format, value=m_val)
                    worksheet_kpi.write_formula(f'H{row}', f'=IF(F{row}>0, E{row}/F{row}, 0)', pct_format, value=v_val)
                    worksheet_kpi.write_formula(f'I{row}', f'=E{row}*D{row}', currency_format, value=r_val)
                    worksheet_kpi.write_formula(f'J{row}', f'=C{row}*E{row}', currency_format, value=t_val)
                    
                    stefna_formula = f'=IF(D{row}=0, "❔ Vantar gögn", IF(AND(D{row}>=0.8, H{row}<1), "🔴 Hækka verð strax!", IF(AND(D{row}>=0.8, H{row}>=1), "🟢 Sterk staða - Halda verði", IF(AND(D{row}<0.4, H{row}>1.05), "🔵 Lækka verð / Búa til tilboð", IF(AND(D{row}<0.4, H{row}<=1), "🟡 Ódýr, en engin sala.", "🟡 Fylgjast með markaði")))))'
                    worksheet_kpi.write_formula(f'K{row}', stefna_formula, value=s_val)

                tot_row = num_rows + 2
                worksheet_kpi.write(f'B{tot_row}', 'SAMTALS / MEÐALTAL', bold_format)
                
                sum_c = kpi_editable['Seld herbergi'].sum()
                avg_d = kpi_editable['Nýting (%)'].mean() / 100
                avg_e = kpi_editable['Mitt_Verð'].mean()
                avg_f = kpi_editable['Keppinautar_Meðalverð'].mean()
                avg_g = kpi_editable['Verðmismunur (ISK)'].mean()
                avg_h = (avg_e / avg_f) if avg_f > 0 else 0
                avg_i = kpi_editable['RevPAR (ISK)'].mean()
                sum_j = kpi_editable['Heildartekjur (ISK)'].sum()

                worksheet_kpi.write_formula(f'C{tot_row}', f'=SUM(C2:C{tot_row-1})', value=sum_c)
                worksheet_kpi.write_formula(f'D{tot_row}', f'=AVERAGE(D2:D{tot_row-1})', pct_format, value=avg_d)
                worksheet_kpi.write_formula(f'E{tot_row}', f'=AVERAGE(E2:E{tot_row-1})', currency_format, value=avg_e)
                worksheet_kpi.write_formula(f'F{tot_row}', f'=AVERAGE(F2:F{tot_row-1})', currency_format, value=avg_f)
                worksheet_kpi.write_formula(f'G{tot_row}', f'=AVERAGE(G2:G{tot_row-1})', currency_format, value=avg_g)
                worksheet_kpi.write_formula(f'H{tot_row}', f'=AVERAGE(H2:H{tot_row-1})', pct_format, value=avg_h)
                worksheet_kpi.write_formula(f'I{tot_row}', f'=AVERAGE(I2:I{tot_row-1})', currency_format, value=avg_i)
                worksheet_kpi.write_formula(f'J{tot_row}', f'=SUM(J2:J{tot_row-1})', currency_format, value=sum_j)

                worksheet_kpi.conditional_format(f'K2:K{num_rows+1}', {'type': 'text', 'criteria': 'containing', 'value': 'Sterk staða', 'format': format_green})
                worksheet_kpi.conditional_format(f'K2:K{num_rows+1}', {'type': 'text', 'criteria': 'containing', 'value': 'Hækka verð', 'format': format_red})
                worksheet_kpi.conditional_format(f'K2:K{num_rows+1}', {'type': 'text', 'criteria': 'containing', 'value': 'Lækka verð', 'format': format_yellow})
                worksheet_kpi.conditional_format(f'K2:K{num_rows+1}', {'type': 'text', 'criteria': 'containing', 'value': 'Ódýr', 'format': format_yellow})

                worksheet_kpi.set_column('A:B', 12)
                worksheet_kpi.set_column('C:J', 15)
                worksheet_kpi.set_column('K:K', 35)

                df_pivot_excel = df_laust.pivot_table(index=['Dagsetning_obj', 'Vikudagur'], columns='Hótel', values='Verð (ISK)', aggfunc='first').reset_index()
                df_pivot_excel['Dagsetning'] = pd.to_datetime(df_pivot_excel['Dagsetning_obj']).dt.date
                df_pivot_excel = df_pivot_excel.drop(columns=['Dagsetning_obj']).set_index(['Dagsetning', 'Vikudagur'])
                df_pivot_excel.to_excel(writer, sheet_name='Verðfylki (Matrix)')
                
                gogn_ut = df[['Dagsetning_obj', 'Vikudagur', 'Hótel', 'Fjöldi herbergja', 'Verð (ISK)', 'Staða']].copy()
                gogn_ut.rename(columns={'Dagsetning_obj': 'Dagsetning'}, inplace=True)
                gogn_ut['Dagsetning'] = pd.to_datetime(gogn_ut['Dagsetning']).dt.date 
                gogn_ut.to_excel(writer, sheet_name='Öll gögn (Hrá)', index=False)

                medaltal_ut = df_saman[['Dagsetning', 'Vikudagur', 'Venjulegt', 'Vegið']].copy()
                medaltal_ut.rename(columns={'Venjulegt': 'Venjulegt meðalverð', 'Vegið': 'Vegið meðalverð'}, inplace=True)
                medaltal_ut.to_excel(writer, sheet_name='Meðalverð Allra', index=False)
                
                worksheet1 = writer.sheets['Meðalverð Allra']
                chart1 = workbook.add_chart({'type': 'column'})
                max_row1 = len(medaltal_ut)
                chart1.add_series({'name': ['Meðalverð Allra', 0, 2], 'categories': ['Meðalverð Allra', 1, 0, max_row1, 0], 'values': ['Meðalverð Allra', 1, 2, max_row1, 2], 'fill': {'color': '#4C78A8'} })
                chart1.add_series({'name': ['Meðalverð Allra', 0, 3], 'categories': ['Meðalverð Allra', 1, 0, max_row1, 0], 'values': ['Meðalverð Allra', 1, 3, max_row1, 3], 'fill': {'color': '#E45756'} })
                chart1.set_title({'name': 'Meðalverð á markaðnum'})
                chart1.set_size({'width': 720, 'height': 400})
                worksheet1.insert_chart('F2', chart1)

                skyrsla_ut = df_skyrsla[['Dagsetning', 'Vikudagur', 'Mitt_Verð', 'Keppinautar_Meðalverð', 'Verðmismunur (ISK)', 'Verðvísitala (%)']].copy()
                skyrsla_ut.rename(columns={'Mitt_Verð': 'Mitt Hótel (ISK)', 'Keppinautar_Meðalverð': 'Keppinautar Vegið (ISK)'}, inplace=True)
                skyrsla_ut.to_excel(writer, sheet_name='Verðvísitala', index=False)
                
                worksheet2 = writer.sheets['Verðvísitala']
                chart2 = workbook.add_chart({'type': 'line'})
                max_row2 = len(skyrsla_ut)
                chart2.add_series({'name': ['Verðvísitala', 0, 2], 'categories': ['Verðvísitala', 1, 0, max_row2, 0], 'values': ['Verðvísitala', 1, 2, max_row2, 2], 'line': {'color': '#1f77b4', 'width': 2.5} })
                chart2.add_series({'name': ['Verðvísitala', 0, 3], 'categories': ['Verðvísitala', 1, 0, max_row2, 0], 'values': ['Verðvísitala', 1, 3, max_row2, 3], 'line': {'color': '#d62728', 'width': 2.5, 'dash_type': 'dash'} })
                chart2.set_title({'name': 'Mitt Hótel vs. Keppinautar'})
                chart2.set_size({'width': 720, 'height': 400})
                worksheet2.insert_chart('H2', chart2)
            
            excel_data = output.getvalue()
            
            st.download_button(
                label=f"Sækja Advanced Mega Skýrslu ({st.session_state['dagar_valdir']} dagar)",
                data=excel_data,
                file_name=f"Advanced_Revenue_Report_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if athuga_lykilord():
    main()
