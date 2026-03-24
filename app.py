import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 1. Breyta nafninu
st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

def main():
    # 1. Breyta nafninu á stjórnborðinu
    st.title("🏨 Hótelstjórinn markaðsverð")

    # Hér setjum við upp sýnidæmi af gögnum (þú setur þín API gögn hér í staðinn)
    gogn = {
        'Dagsetning': ['24.03', '25.03', '26.03', '24.03', '25.03', '26.03'],
        'Hótel': ['Hotel Hamar', 'Hotel Hamar', 'Hotel Hamar', 'Hótel Vesturland', 'Hótel Vesturland', 'Hótel Vesturland'],
        'Verð (ISK)': [24846.9584, 0, 25148.6449, 32638.9023, 32638.9023, 0] # 0 þýðir uppselt í þessu dæmi
    }
    df = pd.DataFrame(gogn)

    st.sidebar.header("Leit")
    
    # 5. Sleppa við að ýta á Enter - Notum fjölval (multiselect) með flettilista í staðinn
    oll_hotel = df['Hótel'].unique().tolist()
    valin_hotel = st.sidebar.multiselect("Leita að gististað", options=oll_hotel, default=oll_hotel)

    # Síum gögnin eftir því hvað er valið
    df_filt = df[df['Hótel'].isin(valin_hotel)].copy()

    if not df_filt.empty:
        
        # 2. Laga "Uppselt" stöðuna. Ef verð er > 0 þá er laust.
        df_filt['Staða'] = np.where(df_filt['Verð (ISK)'] > 0, 'Laust', 'Uppselt')

        # 3. Taka út aukastafi og setja punkt
        # Pössum að breyta yfir í heiltölu (int) til að henda aukastöfum
        df_filt['Verð (ISK)'] = pd.to_numeric(df_filt['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
        # Búum til fallegt útlit fyrir töfluna (t.d. 24.846)
        df_filt['Verð sýnt'] = df_filt['Verð (ISK)'].apply(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "")

        st.subheader("Verðyfirlit")
        # Sýnum töfluna en felum upprunalega dálkinn með ljótu tölunum
        st.dataframe(df_filt[['Dagsetning', 'Hótel', 'Verð sýnt', 'Staða']], use_container_width=True)

        # 4. Reikna meðalverð fyrir hvern dag fyrir ÖLL valin hótel
        st.subheader("Meðalverð markaðar (Samanlagt fyrir valin hótel)")
        # Finnum meðaltal, en tökum 0 (uppselt) út úr jöfnunni
        df_laust = df_filt[df_filt['Verð (ISK)'] > 0]
        
        if not df_laust.empty:
            df_medaltal = df_laust.groupby('Dagsetning')['Verð (ISK)'].mean().reset_index()
            # Hendum aukastöfum og setjum punkt
            df_medaltal['Verð (ISK)'] = df_medaltal['Verð (ISK)'].round(0).astype(int)
            df_medaltal['Meðalverð'] = df_medaltal['Verð (ISK)'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
            
            # Sýnum meðalverðið
            st.dataframe(df_medaltal[['Dagsetning', 'Meðalverð']], use_container_width=True)

            # --- LÍNURIT ---
            st.subheader("Verðþróun")
            fig = px.line(df_filt, x='Dagsetning', y='Verð (ISK)', color='Hótel', markers=True)
            
            # Bætum meðalverðinu við sem svartri, brotinni línu í línuritið
            fig.add_scatter(x=df_medaltal['Dagsetning'], y=df_medaltal['Verð (ISK)'], 
                            mode='lines+markers', name='Meðalverð', 
                            line=dict(color='black', dash='dash', width=3))
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Allt uppselt hjá völdum hótelum!")
    else:
        st.info("Vinsamlegast veldu að minnsta kosti eitt hótel til að skoða gögn.")

if __name__ == "__main__":
    main()
