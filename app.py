import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

def main():
    st.title("🏨 Hótelstjórinn markaðsverð")

    # --- DUMMY GÖGN (Núna með alvöru dagsetningum svo dagatalið virki) ---
    idag = datetime.date.today()
    dagur2 = idag + datetime.timedelta(days=1)
    dagur3 = idag + datetime.timedelta(days=2)

    gogn = {
        'Dagsetning': [idag, dagur2, dagur3, idag, dagur2, dagur3],
        'Hótel': ['Hotel Hamar', 'Hotel Hamar', 'Hotel Hamar', 'Hótel Vesturland', 'Hótel Vesturland', 'Hótel Vesturland'],
        'Verð (ISK)': [24846.9584, 0, 25148.6449, 32638.9023, 32638.9023, 0] 
    }
    df = pd.DataFrame(gogn)

    # --- HLIÐARSTIKA (LEIT OG DAGATAL) ---
    st.sidebar.header("Stillingar")
    
    # 1. Leitin
    leitarord = st.sidebar.text_input("Leita að gististað (ýttu á Enter)")

    # 2. Dagatalið (Leyfir notanda að velja tímabil)
    valin_dagsetning = st.sidebar.date_input(
        "Veldu upphafs- og lokadag",
        value=(idag, dagur3), # Sjálfgefið tímabil þegar síðan opnast
        format="DD.MM.YYYY"
    )

    # --- GAGNASÍA (FILTERING) ---
    # Gætum þess að notandinn hafi valið BÆÐI upphafs- og lokadag í dagatalinu
    if len(valin_dagsetning) == 2:
        upphaf, endir = valin_dagsetning
        
        # Síum gögnin eftir tímabilinu sem var valið
        df_filt = df[(df['Dagsetning'] >= upphaf) & (df['Dagsetning'] <= endir)].copy()
        
        # Síum gögnin eftir leitarorði (ef eitthvað er slegið inn)
        if leitarord:
            df_filt = df_filt[df_filt['Hótel'].str.contains(leitarord, case=False, na=False)]

        # --- VINNSLA Á GÖGNUM TIL SÝNINGAR ---
        if not df_filt.empty:
            # Laga "Uppselt" og fínpússa tölur
            df_filt['Staða'] = np.where(df_filt['Verð (ISK)'] > 0, 'Laust', 'Uppselt')
            df_filt['Verð (ISK)'] = pd.to_numeric(df_filt['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
            df_filt['Verð sýnt'] = df_filt['Verð (ISK)'].apply(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "")

            # Breytum dagsetningunni í flottara format ("24.03") bara fyrir töfluna/línuritið
            df_filt['Dagsetning_str'] = df_filt['Dagsetning'].apply(lambda x: x.strftime("%d.%m"))

            # Lögum talningu (byrjar á 1)
            df_filt.index = np.arange(1, len(df_filt) + 1)

            st.subheader("Verðyfirlit")
            st.dataframe(df_filt[['Dagsetning_str', 'Hótel', 'Verð sýnt', 'Staða']], use_container_width=True)

            # --- MEÐALVERÐ ---
            st.subheader("Meðalverð markaðar (Samanlagt fyrir valin hótel)")
            df_laust = df_filt[df_filt['Verð (ISK)'] > 0]
            
            if not df_laust.empty:
                df_medaltal = df_laust.groupby('Dagsetning_str')['Verð (ISK)'].mean().reset_index()
                df_medaltal['Verð (ISK)'] = df_medaltal['Verð (ISK)'].round(0).astype(int)
                df_medaltal['Meðalverð'] = df_medaltal['Verð (ISK)'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
                
                # Talningin fyrir meðalverð (byrjar á 1)
                df_medaltal.index = np.arange(1, len(df_medaltal) + 1)
                
                st.dataframe(df_medaltal[['Dagsetning_str', 'Meðalverð']], use_container_width=True)

                # --- LÍNURIT ---
                st.subheader("Verðþróun")
                fig = px.line(df_filt, x='Dagsetning_str', y='Verð (ISK)', color='Hótel', markers=True)
                fig.add_scatter(x=df_medaltal['Dagsetning_str'], y=df_medaltal['Verð (ISK)'], 
                                mode='lines+markers', name='Meðalverð', 
                                line=dict(color='black', dash='dash', width=3))
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Allt uppselt hjá völdum hótelum á þessu tímabili!")
        else:
            st.info("Ekkert hótel fannst eða engin gögn á völdu tímabili.")
    else:
        st.info("Vinsamlegast veldu lokadag í dagatalinu til að birta gögn.")

if __name__ == "__main__":
    main()
