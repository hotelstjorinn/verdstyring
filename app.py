import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

def main():
    st.title("🏨 Hótelstjórinn markaðsverð")

    # --- HLIÐARSTIKA (LEIT OG DAGATAL) ---
    st.sidebar.header("Stillingar")
    
    # Leitin (Venjulegt textabox)
    leitarord = st.sidebar.text_input("Leita að gististað (ýttu á Enter)")

    # Dagatalið (Sjálfgefið í dag til næstu 7 daga)
    idag = datetime.date.today()
    valin_dagsetning = st.sidebar.date_input(
        "Veldu upphafs- og lokadag",
        value=(idag, idag + datetime.timedelta(days=7)), 
        format="DD.MM.YYYY"
    )

    # ==========================================
    # ⚠️ HÉR ÞARFT ÞÚ AÐ SETJA ÞÍN GÖGN INN ⚠️
    # ==========================================
    # Í staðinn fyrir að setja Hótel Hamar fast inn, bý ég hér til algjörlega TÓMA töflu.
    # Þú þarft að láta þinn eigin kóða (sem sækir verðin af netinu) búa til 
    # DataFrame sem heitir 'df' og inniheldur dálkana: ['Dagsetning', 'Hótel', 'Verð (ISK)']
    
    df = pd.DataFrame(columns=['Dagsetning', 'Hótel', 'Verð (ISK)'])
    
    # DÆMI UM HVAÐ ÞÚ GÆTIR ÞURFT AÐ GERA:
    # ef leitarord:
    #     df = minn_gagnasaekir_kodi(leitarord, upphaf, endir)
    # ==========================================

    # --- VINNSLA Á GÖGNUM TIL SÝNINGAR ---
    if len(valin_dagsetning) == 2:
        upphaf, endir = valin_dagsetning
        
        # Pössum að við höfum einhver gögn til að vinna með áður en við höldum áfram
        if not df.empty:
            
            # Gætum þess að dagsetningin sé á réttu formi til að hægt sé að sía hana
            df['Dagsetning'] = pd.to_datetime(df['Dagsetning']).dt.date
            
            # Síum gögnin eftir tímabilinu úr dagatalinu
            df_filt = df[(df['Dagsetning'] >= upphaf) & (df['Dagsetning'] <= endir)].copy()
            
            # Síum eftir leitarorði ef við á (ef API-ið þitt skilar mörgum niðurstöðum)
            if leitarord:
                df_filt = df_filt[df_filt['Hótel'].str.contains(leitarord, case=False, na=False)]

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
                st.info("Engin gögn fundust fyrir þessa leit.")
        else:
            st.info("Leitaðu að hóteli til að byrja að safna gögnum.")
    else:
        st.info("Vinsamlegast veldu bæði upphafs- og lokadag í dagatalinu.")

if __name__ == "__main__":
    main()
