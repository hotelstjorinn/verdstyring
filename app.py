import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime
import requests
from bs4 import BeautifulSoup
import urllib.parse
import re

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
def saekja_med_skofun(hotel_listi, fjoldi_daga):
    idag = datetime.date.today()
    gogn = []
    
    # Við þykjumst vera venjulegur vafri svo Booking loki ekki á okkur strax
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "is-IS,is;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": "https://www.booking.com/"
    }
    
    for hotel in hotel_listi:
        st.info(f"📍 Sendi vélmenni beint á Booking.com til að leita að: **{hotel}**")
        
        for i in range(fjoldi_daga):
            checkin_dagur = idag + datetime.timedelta(days=i)
            checkout_dagur = checkin_dagur + datetime.timedelta(days=1)
            
            checkin_str = checkin_dagur.strftime("%Y-%m-%d")
            checkout_str = checkout_dagur.strftime("%Y-%m-%d")
            
            # Smíðum nákvæmlega sömu slóð og þú myndir slá inn í vafrann þinn
            hotel_encoded = urllib.parse.quote_plus(hotel)
            url = f"https://www.booking.com/searchresults.is.html?ss={hotel_encoded}&checkin={checkin_str}&checkout={checkout_str}&group_adults=2&no_rooms=1&group_children=0&currency=ISK"
            
            try:
                # Sækjum vefsíðuna beint
                res = requests.get(url, headers=headers, timeout=15)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                verd = 0
                
                # Athugum hvort Booking sé að heimta CAPTCHA (að sanna að við séum mennsk)
                if "px-captcha" in res.text or "Verify you are human" in res.text:
                    with st.expander(f"⚠️ Booking.com stoppaði vélmennið okkar þann {checkin_dagur.strftime('%d.%m')}"):
                        st.error("Booking fór í vörn og bað um CAPTCHA staðfestingu. Vefskröpun var stöðvuð.")
                        st.write(f"Slóðin sem við reyndum: {url}")
                else:
                    # Leitum að verðinu í HTML kóðanum. Booking notar oft þennan 'data-testid' fyrir verð í leitarvél
                    price_element = soup.find(attrs={"data-testid": "price-and-discounted-price"})
                    
                    if price_element:
                        # Hreinsum textann ("ISK 21.778" -> 21778)
                        price_text = price_element.get_text()
                        tala_str = re.sub(r'[^\d]', '', price_text)
                        if tala_str.isdigit():
                            verd = int(tala_str)
                    else:
                        # Ef við finnum ekki price-elementið, þá er annað hvort uppselt EÐA Booking breytti útlitinu hjá sér
                        with st.expander(f"🔍 Fann ekki verð á vefsíðunni þann {checkin_dagur.strftime('%d.%m')} (Mögulega uppselt)"):
                            st.write(f"Skoðaðu þessa slóð sjálf/ur til að staðfesta hvort það sé raunverulega uppselt eða hvort okkur tókst ekki að lesa verðið:")
                            st.markdown(f"[Smelltu hér til að opna Booking.com fyrir þennan dag]({url})")
                
                herbergi = 50 
                
                gogn.append({
                    "Dagsetning": checkin_dagur, 
                    "Hótel": hotel, 
                    "Verð (ISK)": verd, 
                    "Fjöldi herbergja": herbergi
                })
                
            except Exception as e:
                st.error(f"Villa við að skrapa vefsíðu fyrir {hotel} þann {checkin_str}: {e}")
            
    return pd.DataFrame(gogn)
# ==========================================

def main():
    st.title("🏨 Hótelstjórinn markaðsverð (Bein skröpun)")

    if 'valin_hotel' not in st.session_state:
        st.session_state['valin_hotel'] = []

    st.sidebar.header("Leit")
    
    nytt_hotel = st.sidebar.text_input("Bæta við gististað (ýttu á Enter)")
    
    if nytt_hotel and nytt_hotel not in st.session_state['valin_hotel']:
        st.session_state['valin_hotel'].append(nytt_hotel)

    if len(st.session_state['valin_hotel']) > 0:
        st.sidebar.markdown("### Valdir gististaðir:")
        for i, hotel in enumerate(st.session_state['valin_hotel']):
            st.sidebar.markdown(f"- **{hotel}**")
            
        if st.sidebar.button("Hreinsa allan lista"):
            st.session_state['valin_hotel'] = []
            st.rerun()

    col1, col2, col3 = st.columns(3)
    with col1:
        btn_1 = st.button("Sækja verð núna")
    with col2:
        btn_7 = st.button("Sækja verð næstu 7 daga")
    with col3:
        btn_30 = st.button("Sækja verð næstu 30 daga")

    dagar_valdir = 0
    if btn_1: dagar_valdir = 1
    elif btn_7: dagar_valdir = 7
    elif btn_30: dagar_valdir = 30

    if dagar_valdir > 0:
        if len(st.session_state['valin_hotel']) > 0:
            st.success(f"Beini vöfrum að Booking.com fyrir **{len(st.session_state['valin_hotel'])}** gististaði í **{dagar_valdir}** daga. Þetta gæti tekið smá stund...")
            
            df = saekja_med_skofun(st.session_state['valin_hotel'], dagar_valdir) 

            if not df.empty:
                df['Staða'] = np.where(df['Verð (ISK)'] > 0, 'Laust', 'Uppselt / Fannst ekki')
                df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
                
                df['Verð sýnt'] = df['Verð (ISK)'].apply(
                    lambda x: f"{x:,}".replace(",", ".") if x > 0 else ""
                )
                
                df['Dagsetning_str'] = pd.to_datetime(df['Dagsetning']).dt.strftime("%d.%m")
                df.index = np.arange(1, len(df) + 1)

                st.subheader(f"Verðyfirlit ({dagar_valdir} dagar)")
                
                syndir_dalkar = [
                    'Dagsetning_str', 'Hótel', 'Fjöldi herbergja', 'Verð sýnt', 'Staða'
                ]
                st.dataframe(df[syndir_dalkar], use_container_width=True)

                st.subheader("Meðalverð markaðar (Venjulegt og Vegið)")
                df_laust = df[df['Verð (ISK)'] > 0].copy()
                
                if not df_laust.empty:
                    df_medaltal = df_laust.groupby('Dagsetning_str')['Verð (ISK)'].mean().reset_index()
                    df_medaltal.rename(columns={'Verð (ISK)': 'Venjulegt meðalverð'}, inplace=True)

                    df_laust['Verð_Vægi'] = df_laust['Verð (ISK)'] * df_laust['Fjöldi herbergja']
                    
                    df_veg = df_laust.groupby('Dagsetning_str').agg(
                        Summa_Verð_Vægi=('Verð_Vægi', 'sum'),
                        Summa_Herbergi=('Fjöldi herbergja', 'sum')
                    ).reset_index()
                    
                    df_veg['Vegið meðalverð'] = df_veg['Summa_Verð_Vægi'] / df_veg['Summa_Herbergi']

                    df_saman = pd.merge(df_medaltal, df_veg[['Dagsetning_str', 'Vegið meðalverð']], on='Dagsetning_str')
                    
                    df_saman['Venjulegt meðalverð'] = df_saman['Venjulegt meðalverð'].round(0).astype(int)
                    df_saman['Vegið meðalverð'] = df_saman['Vegið meðalverð'].round(0).astype(int)

                    df_saman['Venjulegt (sýnt)'] = df_saman['Venjulegt meðalverð'].apply(
                        lambda x: f"{x:,} ISK".replace(",", ".")
                    )
                    df_saman['Vegið (sýnt)'] = df_saman['Vegið meðalverð'].apply(
                        lambda x: f"{x:,} ISK".replace(",", ".")
                    )
                    df_saman.index = np.arange(1, len(df_saman) + 1)
                    
                    syndir_dalkar_saman = ['Dagsetning_str', 'Venjulegt (sýnt)', 'Vegið (sýnt)']
                    st.dataframe(df_saman[syndir_dalkar_saman], use_container_width=True)

                    st.subheader("Verðþróun")
                    fig = px.bar(df, x='Dagsetning_str', y='Verð (ISK)', color='Hótel', barmode='group')
                    
                    fig.add_scatter(
                        x=df_saman['Dagsetning_str'], y=df_saman['Venjulegt meðalverð'], 
                        mode='lines+markers', name='Venjulegt meðaltal', 
                        line=dict(color='black', dash='dash', width=2)
                    )
                    
                    fig.add_scatter(
                        x=df_saman['Dagsetning_str'], y=df_saman['Vegið meðalverð'], 
                        mode='lines+markers', name='Vegið meðaltal', 
                        line=dict(color='red', width=3)
                    )
                    
                    fig.update_yaxes(rangemode="tozero")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Ekkert verð fannst (Mögulega lokaði Booking á okkur, eða allt er uppselt).")
        else:
            st.error("Þú þarft að bæta við að minnsta kosti einum gististað vinstra megin áður en þú leitar!")

if __name__ == "__main__":
    main()
