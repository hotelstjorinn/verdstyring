import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import requests

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
def saekja_raungogn(hotel_listi, fjoldi_daga):
    API_KEY = "aa73991419msh780ae4bacd33dc3p12ac5fjsn494bf3cba6a6"
    idag = datetime.date.today()
    gogn = []
    
    headers = {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"
    }
    
    for hotel in hotel_listi:
        try:
            url_loc = "https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete"
            qs_loc = {"text": hotel, "languagecode": "is"}
            
            res_loc = requests.get(url_loc, headers=headers, params=qs_loc)
            data_loc = res_loc.json()
            
            if not data_loc or len(data_loc) == 0:
                st.warning(f"Booking fann ekki gististaðinn: '{hotel}'")
                continue
                
            dest_id = data_loc[0].get("dest_id")
            search_type = data_loc[0].get("dest_type", "hotel") 
            fundid_nafn = data_loc[0].get("name", hotel)
            
            st.info(f"📍 Leita að lausum herbergjum á: **{fundid_nafn}** (ID: {dest_id}, Tegund: {search_type})")
            
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
                    "dest_ids": str(dest_id),  
                    "search_type": search_type, 
                    "currency": "ISK",
                    "locale": "en-gb",
                    "children_qty": "0" 
                }
                
                res_list = requests.get(url_list, headers=headers, params=qs_list)
                data_list = res_list.json()
                
                verd = 0 
                
                if "result" in data_list and len(data_list["result"]) > 0:
                    hotel_data = data_list["result"][0]
                    
                    if "composite_price_breakdown" in hotel_data and "gross_amount" in hotel_data["composite_price_breakdown"]:
                        verd = hotel_data["composite_price_breakdown"]["gross_amount"].get("value", 0)
                    elif "priceBreakdown" in hotel_data and "grossPrice" in hotel_data["priceBreakdown"]:
                        verd = hotel_data["priceBreakdown"]["grossPrice"].get("value", 0)
                    elif "min_total_price" in hotel_data:
                        verd = hotel_data.get("min_total_price", 0)
                    
                    if not verd or verd == 0:
                        with st.expander(f"🔍 Fann hótelið en vantar verð fyrir {checkin_dagur.strftime('%d.%m')}"):
                            st.write("Gögnin um hótelið litu svona út. Hvar er verðið falið?")
                            st.json(hotel_data)
                        verd = 0
                else:
                    with st.expander(f"🔍 Sjá ALLT svarið frá Booking fyrir {checkin_dagur.strftime('%d.%m')}"):
                        st.write("Booking API svaraði með tómum lista.")
                        st.write("Hér er allt JSON svarið. Gefðu mér skjáskot af þessu:")
                        st.json(data_list)
                
                herbergi = 50 
                
                gogn.append({
                    "Dagsetning": checkin_dagur, 
                    "Hótel": hotel, 
                    "Verð (ISK)": verd, 
                    "Fjöldi herbergja": herbergi
                })
                    
        except Exception as e:
            st.error
