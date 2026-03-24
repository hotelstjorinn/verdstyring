import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Verðstýring 30 Dagar", layout="wide")

st.title("📈 30-Daga Verðstýring og Spá")

# --- 1. STJÓRNANDI (SIDEBAR) ---
st.sidebar.header("Stillingar")
mitt_markmid = st.sidebar.slider("Verðstefna (% af meðalverði)", 50, 150, 95)
st.sidebar.info("95% þýðir að þú vilt vera 5% ódýrari en meðaltalið.")

# --- 2. GÖGN (SIMULATION - Þar sem scraping á 30 daga tekur tíma) ---
# Í alvöru appi myndum við keyra loopu sem sækir 30 daga af Booking/Google
dates = [datetime.now() + timedelta(days=i) for i in range(30)]
hotel_names = ["Hótel Hamar", "B59 Hotel", "Hotel Egilsen", "Borgarnes HI", "Blómasetrið", "Kyrjala", "Hótel fimm", "Gisti X", "Gisti Y", "Gisti Z"]

# Búum til sýnidæmi af 30 daga gögnum
if 'market_data' not in st.session_state:
    data = []
    for d in dates:
        base_price = 25000 + (np.sin(d.day) * 5000) # Smá sveiflur
        for h in hotel_names:
            price = base_price + np.random.randint(-3000, 3000)
            data.append({"Dagsetning": d.date(), "Hótel": h, "Verð": price})
    st.session_state.market_data = pd.DataFrame(data)

df = st.session_state.market_data

# --- 3. GREINING ---
# Reiknum meðaltal fyrir hvern dag
daily_summary = df.groupby('Dagsetning')['Verð'].mean().reset_index()
daily_summary.columns = ['Dagsetning', 'Meðalverð Markaðar']

# Reiknum tillögu að verði
daily_summary['Mælt með (Þitt verð)'] = daily_summary['Meðalverð Markaðar'] * (mitt_markmid / 100)

# --- 4. BIRTING ---
st.subheader("Ráðleggingar fyrir næstu 30 daga")

# Línurit sem sýnir þróunina
st.line_chart(daily_summary.set_index('Dagsetning'))

# Tafla með nákvæmum tölum
col1, col2 = st.columns([2, 1])

with col1:
    st.write("Dagleg sundurliðun")
    st.dataframe(daily_summary.style.format({
        'Meðalverð Markaðar': '{:,.0f} kr.',
        'Mælt með (Þitt verð)': '{:,.0f} kr.'
    }), use_container_width=True)

with col2:
    st.write("Hæsta eftirspurn (Top 3 dagar)")
    top_days = daily_summary.sort_values(by='Meðalverð Markaðar', ascending=False).head(3)
    for i, row in top_days.iterrows():
        st.error(f"📅 {row['Dagsetning']}: {row['Meðalverð Markaðar']:,.0f} kr.")
