import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
# ÞETTA ER BARA TIL AÐ SÝNA AÐ LEITIN VIRKI
# (Býr til gervigögn þegar þú ýtir á takkana)
def saekja_gervigogn(hotel_nafn, fjoldi_daga):
    idag = datetime.date.today()
    gogn = []
    for i in range(fjoldi_daga):
        dagur = idag + datetime.timedelta(days=i)
        # Býr til slembi-verð til að sýna eitthvað í töflunni (0 = uppselt)
        verd = np.random.choice([0, 24846, 32638, 15000, 28000]) 
        gogn.append({"Dagsetning": dagur, "Hótel": hotel_nafn, "Verð (ISK)": verd})
    return pd.DataFrame(gogn)
# ==========================================

def main():
    st.title("🏨 Hótelstjórinn markaðsverð")

    # --- LEITIN (Venjulegt textabox, þarft að ýta á Enter) ---
    st.sidebar.header("Leit")
    leitarord = st.sidebar.text_input("Leita að gististað (ýttu á Enter)")

    # --- TAKKAR FYRIR DAGA (Eins og á fyrstu myndinni þinni) ---
    col1, col2, col3 = st.columns(3)
    with col1:
        btn_1 = st.button("Sækja verð markaðar núna")
    with col2:
        btn_7 = st.button("Sækja verð markaðar næstu 7 daga")
    with col3:
        btn_30 = st.button("Sækja verð markaðar næstu 30 daga")

    # Finnum út hvaða takka var ýtt á
    dagar_valdir = 0
    if btn_1:
        dagar_valdir = 1
    elif btn_7:
        dagar_valdir = 7
    elif btn_30:
        dagar_valdir = 30

    # Ef notandi hefur skrifað inn leitarorð OG ýtt á takka
    if leitarord and dagar_valdir > 0:
        st.success(f"Leita að: **{leitarord}** fyrir næstu **{dagar_valdir}** daga. Bíddu andartak...")
        
        # ==========================================
        # ⚠️ HÉR KEMUR ÞINN KÓÐI SEM SÆKIR GÖGNIN AF NETINU ⚠️
        # Þú eyðir út línunni hér að neðan og lætur þitt eigið forrit 
        # búa til DataFrame sem heitir 'df' út frá leitarorðinu og dögunum.
        
        df = saekja_gervigogn(leitarord, dagar_valdir) 
        
        # ==========================================

        # --- VINNSLA Á GÖGNUM TIL SÝNINGAR ---
        if not df.empty:
            # Laga "Uppselt" og fínpússa tölur
            df['Staða'] = np.where(df['Verð (ISK)'] > 0, 'Laust', 'Uppselt')
            df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
            df['Verð sýnt'] = df['Verð (ISK)'].apply(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "")

            # Breytum dagsetningunni í flottara format ("24.03") 
            df['Dagsetning_str'] = pd.to_datetime(df['Dagsetning']).dt.strftime("%d.%m")

            # Lögum talningu (byrjar á 1)
            df.index = np.arange(1, len(df) + 1)

            st.subheader(f"Verðyfirlit ({dagar_valdir} dagar)")
            st.dataframe(df[['Dagsetning_str', 'Hótel', 'Verð sýnt', 'Staða']], use_container_width=True)

            # --- MEÐALVERÐ ---
            st.subheader("Meðalverð markaðar (Samanlagt fyrir valin hótel)")
            df_laust = df[df['Verð (ISK)'] > 0]
            
            if not df_laust.empty:
                df_medaltal = df_laust.groupby('Dagsetning_str')['Verð (ISK)'].mean().reset_index()
                df_medaltal['Verð (ISK)'] = df_medaltal['Verð (ISK)'].round(0).astype(int)
                df_medaltal['Meðalverð'] = df_medaltal['Verð (ISK)'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
                
                df_medaltal.index = np.arange(1, len(df_medaltal) + 1)
                st.dataframe(df_medaltal[['Dagsetning_str', 'Meðalverð']], use_container_width=True)

                # --- LÍNURIT ---
                st.subheader("Verðþróun")
                fig = px.line(df, x='Dagsetning_str', y='Verð (ISK)', color='Hótel', markers=True)
                fig.add_scatter(x=df_medaltal['Dagsetning_str'], y=df_medaltal['Verð (ISK)'], 
                                mode='lines+markers', name='Meðalverð', 
                                line=dict(color='black', dash='dash', width=3))
                
                # Pössum að y-ásinn byrji á 0 svo verðið líti eðlilega út
                fig.update_yaxes(rangemode="tozero")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("Allt uppselt á völdu tímabili!")
        else:
            st.info("Engin gögn fundust fyrir þessa leit.")
            
    elif not leitarord:
        st.info("Sláðu inn nafn á hóteli vinstra megin og ýttu svo á einn af tökkunum til að sækja gögn.")

if __name__ == "__main__":
    main()
