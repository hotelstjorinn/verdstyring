import streamlit as st
import pandas as pd

st.set_page_config(page_title="Verðstýring Borgarnes", layout="centered")

st.title("🏨 Verðstýring Borgarnes")
st.write("Velkomin(n) í þitt eigið verðstýringar-app!")

# Hér eru prufugögn (við tengjum raunveruleg gögn síðar)
gogn = {
    'Gististaður': ['B59 Hotel', 'Hótel Hamar', 'Hótel Egilsen', 'Mitt Gistiheimili'],
    'Verð (kr.)': [28500, 31200, 26900, 25000],
    'Staða': ['Óbreytt', 'Hækkar', 'Lágt', 'Mitt verð']
}

df = pd.DataFrame(gogn)

st.subheader("Staðan á markaðnum í dag")
st.table(df)

# Myndræn framsetning
st.bar_chart(df.set_index('Gististaður')['Verð (kr.)'])

st.success("Appið er virkt! Næsta skref er að tengja sjálfvirka skönnun.")
