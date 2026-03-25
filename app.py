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
# API GAGNASÖFNUN & FLOKKUN (NÝTT VÉLARÚM)
# ==========================================
def saekja_raungogn(hotel_dict, fjoldi_daga):
    API_KEY = "aa73991419msh780ae4bacd33dc3p12ac5fjsn494bf3cba6a6" 
    idag = datetime.date.today()
    gogn = []
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"
    }
    
    st.write("### 📡 Tengist við Booking.com og flokkar herbergi...")
    
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
            st.info(f"📍 **{hotel}** fundið! Booking Nafn: *{fundid_nafn}* | ID: `{dest_id}`")
            
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
                    data_api = res_api.json()
                    
                    if isinstance(data_api, list) and len(data_api) > 0:
                        first_item = data_api[0]
                        rooms_dict = first_item.get("rooms", {})
                        
                        # Geymum lægsta verð fyrir hvern flokk þennan dag
                        flokkar_verd = {"Economy": [], "Standard": [], "Deluxe": [], "Junior Suite": [], "Suite": []}
                        
                        if "block" in first_item and isinstance(first_item["block"], list):
                            for b in first_item["block"]:
                                room_id = str(b.get("room_id", ""))
                                room_name = rooms_dict.get(room_id, {}).get("name", "Standard Room")
                                
                                # FLOKKUNARVÉLIN
                                nafn_l = room_name.lower()
                                if "junior" in nafn_l and ("suit" in nafn_l or "svít" in nafn_l): flokkur = "Junior Suite"
                                elif "suit" in nafn_l or "svít" in nafn_l: flokkur = "Suite"
                                elif any(x in nafn_l for x in ["deluxe", "superior", "premium", "executive"]): flokkur = "Deluxe"
                                elif any(x in nafn_l for x in ["economy", "budget", "basic", "small", "compact"]): flokkur = "Economy"
                                else: flokkur = "Standard"
                                
                                if "product_price_breakdown" in b:
                                    ppb = b["product_price_breakdown"]
                                    if "gross_amount" in ppb and "value" in ppb["gross_amount"]:
                                        flokkar_verd[flokkur].append(ppb["gross_amount"]["value"])
                        
                        # Bæta við öllum herbergjatýpum sem fundust í heildarlistann
                        for fl, verd_listi in flokkar_verd.items():
                            if verd_listi:
                                min_v = min(verd_listi)
                                gogn.append({"Dagsetning_obj": checkin_dagur, "Hótel": hotel, "Herbergjatýpa": fl, "Verð (ISK)": min_v, "Fjöldi herbergja": herbergi})
                else:
                    # Fallback ef ekki finnst nákvæmlega "hotel" API, gerir þá ráð fyrir Standard
                    url_api = "https://apidojo-booking-v1.p.rapidapi.com/properties/list"
                    qs_api = {
                        "offset": "0", "arrival_date": checkin_dagur.strftime("%Y-%m-%d"),
                        "departure_date": checkout_dagur.strftime("%Y-%m-%d"),
                        "guest_qty": "2", "room_qty": "1", "dest_ids": str(dest_id),  
                        "search_type": search_type, "price_filter_currencycode": "ISK", "children_qty": "0"
                    }
                    res_api = requests.get(url_api, headers=headers, params=qs_api)
                    data_api = res_api.json()
                    verd = 0
                    if "result" in data_api and len(data_api["result"]) > 0:
                        hotel_data = data_api["result"][0]
                        if "composite_price_breakdown" in hotel_data and "gross_amount" in hotel_data["composite_price_breakdown"]:
                            verd = hotel_data["composite_price_breakdown"]["gross_amount"].get("value", 0)
                        elif "priceBreakdown" in hotel_data and "grossPrice" in hotel_data["priceBreakdown"]:
                            verd = hotel_data["priceBreakdown"]["grossPrice"].get("value", 0)
                        elif "min_total_price" in hotel_data:
                            verd = hotel_data.get("min_total_price", 0)
                    if verd > 0:
                        gogn.append({"Dagsetning_obj": checkin_dagur, "Hótel": hotel, "Herbergjatýpa": "Standard", "Verð (ISK)": verd, "Fjöldi herbergja": herbergi})
                        
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
    nyr_keppinautur = st.sidebar.text
