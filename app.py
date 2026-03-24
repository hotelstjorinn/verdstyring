import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import requests

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
def saekja_raungogn(hotel_listi, fjoldi_daga):
    # API lykillinn þinn fyrir Apidojo
    API_KEY = "aa73991419msh780ae4bacd33dc3p12ac5fjsn494bf3cba6a6"
    idag = datetime.date.today()
    gogn = []
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"
    }
    
    for hotel in hotel_listi:
        try:
            # --- SKREF 1: Finna auðkenni (ID) hótelsins ---
            url_loc = "https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete"
            qs_loc = {"text": hotel, "languagecode": "is"}
            
            res_loc = requests.get(url_loc, headers=headers, params=qs_loc)
            data_loc = res_loc.json()
            
            if not data_loc or len(data_loc) == 0:
                st.warning(f"Booking fann ekki gististaðinn: '{hotel}'")
                continue
                
            dest_id = data_loc[0].get("dest_id")
            search_type = data_loc[0].get("search_type")
            
            # --- SKREF 2: Sækja verðið DAG FYRIR DAG ---
            # Núna keyrum við API kall fyrir hvern einasta dag (1 nótt í einu)
            for i in range(fjoldi_daga):
                checkin_dagur = idag + datetime.timedelta(days=i)
                checkout_dagur = checkin_dagur + datetime.timedelta(days=1)
                 
                url_list = "https://apidojo-booking-v1.p.rapidapi.com/properties/list"
                qs_list = {
                    "offset": "0",
                    "arrival_date": checkin_dagur.strftime("%Y-%m-%d"),
                    "departure_date": checkout_dagur.strftime("%Y-%m-%d"),
                    "guest_qty": "2", 
                    "room_qty": "1",  
                    "dest_ids": dest_id,
                    "search_type": search_type,
                    "price_filter_currencycode": "ISK" 
                }
                
                res_list = requests.get(url_list, headers=headers, params=qs_list)
                data_list = res_list.json()
                
                verd = 0 # Gerum ráð fyrir að það sé uppselt (0 kr) fyrst
                
                # Ef við fáum svar og herbergi er laust þennan daginn, skráum við verðið
                if "result
