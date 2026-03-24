import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
# GERVIGÖGN - Núna með "Fjölda herbergja" til að geta reiknað vegið meðaltal
def saekja_gervigogn(hotel_listi, fjoldi_daga):
    idag = datetime.date.today()
    gogn = []
    
    # Búum til fastan fjölda herbergja (vægi) fyrir hvert hótel í þessari leit
    hotel_staerdir = {hotel: np.random.randint(20, 150) for hotel in hotel_listi}
    
    for hotel in hotel_listi:
        herbergi = hotel_staerdir[hotel]
        for i in range(fjoldi_daga):
            dagur = idag + datetime.timedelta(days=i)
            verd = np.random.choice([0, 24846, 32638, 15000, 28000, 42000]) 
            gogn.append({"Dagsetning": dagur, "Hótel": hotel, "Verð (ISK)": verd, "Fjöldi herbergja": herbergi})
    return pd.DataFrame(gogn)
# ==========================================

def main():
    st.title("🏨 Hótelstjórinn markaðsverð")

    if 'valin_hotel' not in st.session_state:
        st.session_state['valin_hotel'] = []

    # --- HLIÐARSTIKA (LEIT OG LISTI) ---
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

    # --- TAKKAR FYRIR DAGA ---
    col1, col2, col3 = st.columns(3)
    with col1:
        btn_1 = st.button("Sækja verð markaðar núna")
    with col2:
        btn_7 = st.button("Sækja verð markaðar næstu 7 daga")
    with col3:
        btn_30 = st.button("Sækja verð markaðar næstu 30 daga")

    dagar_valdir = 0
    if btn_1: dagar_valdir = 1
    elif btn_7: dagar_valdir = 7
    elif btn_30: dagar_valdir = 30

    # Ef ýtt var á takka...
    if dagar_valdir > 0:
        if len(st.session_state['valin_hotel']) > 0:
            st.success(f"Sæki gögn fyrir **{len(st.session_state['valin_hotel'])}** gististaði í **{dagar_valdir}** daga. Bíddu andartak...")
            
            # ==========================================
            # ⚠️ HÉR KEMUR ÞINN ALVÖRU KÓÐI ⚠️
            # Til að vegið meðaltal virki þarf þinn kóði að skila dálki sem 
            # heitir "Fjöldi herbergja" eða "Vægi" fyrir hvert hótel!
            df = saekja_gervigogn(st.session_state['valin_hotel'], dagar_valdir) 
            # ==========================================

            if not df.empty:
                # Undirbúum aðaltöfluna
                df['Staða'] = np.where(df['Verð (ISK)'] > 0, 'Laust', 'Uppselt')
                df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
                df['Verð sýnt'] = df['Verð (ISK)'].apply(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "")
                df['Dagsetning_str'] = pd.to_datetime(df['Dagsetning']).dt.strftime("%d.%m")
                df.index = np.arange(1, len(df) + 1)

                st.subheader(f"Verðyfirlit ({dagar_valdir} dagar)")
                # Bætti við Fjölda herbergja í sýnina svo maður sjái vægið
                st.dataframe(df[['Dagsetning_str', 'Hótel', 'Fjöldi herbergja', 'Verð sýnt', 'Staða']], use_container_width=True)

                # --- REIKNUM BÆÐI MEÐALTÖLIN ---
                st.subheader("Meðalverð markaðar (Venjulegt og Vegið)")
                df_laust = df[df['Verð (ISK)'] > 0].copy()
                
                if not df_laust.empty:
                    # 1. Venjulegt meðaltal (óvegið)
                    df_medaltal = df_laust.groupby('Dagsetning_str')['Verð (ISK)'].mean().reset_index()
                    df_medaltal.rename(columns={'Verð (ISK)': 'Venjulegt meðalverð'}, inplace=True)

                    # 2. Vegið meðaltal (Verð * Herbergi / Heildar herbergi)
                    df_laust['Verð_Vægi'] = df_laust['Verð (ISK)'] * df_laust['Fjöldi herbergja']
                    df_veg = df_laust.groupby('Dagsetning_str').agg(
                        Summa_Verð_Vægi=('Verð_Vægi', 'sum'),
                        Summa_Herbergi=('Fjöldi herbergja', 'sum')
                    ).reset_index()
                    df_veg['Vegið meðalverð'] = df_veg['Summa_Verð_Vægi'] / df_veg['Summa_Herbergi']

                    # Sameinum töflurnar
                    df_saman = pd.merge(df_medaltal, df_veg[['Dagsetning_str', 'Vegið meðalverð']], on='Dagsetning_str')
                    
                    # Tökum til aukastafi og setjum upp fyrir töflu
                    df_saman['Venjulegt meðalverð'] = df_saman['Venjulegt meðalverð'].round(0).astype(int)
                    df_saman['Vegið meðalverð'] = df_saman['Vegið meðalverð'].round(0).astype(int)

                    # Búum til flott texta-format fyrir töfluna ("ISK")
                    df_saman['Venjulegt (sýnt)'] = df_saman['Venjulegt meðalverð'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
                    df_saman['Vegið (sýnt)'] = df_saman['Vegið meðalverð'].apply(lambda x: f"{x:,} ISK".replace(",", "."))
                    df_saman.index = np.arange(1, len(df_saman) + 1)
                    
                    st.dataframe(df_saman[['Dagsetning_str', 'Venjulegt (sýnt)', 'Vegið (sýnt)']], use_container_width=True)

                    # --- SÚLURIT MEÐ BÁÐUM LÍNUM ---
                    st.subheader("Verðþróun")
                    fig = px.bar(df, x='Dagsetning_str', y='Verð (ISK)', color='Hótel', barmode='group')
                    
                    # Lína 1: Venjulegt meðaltal (Svört brotin lína)
                    fig.add_scatter(x=df_saman['Dagsetning_str'], y=df_saman['Venjulegt meðalverð'], 
                                    mode='lines+markers', name='Venjulegt meðaltal', 
                                    line=dict(color='black', dash='dash', width=2))
                    
                    # Lína 2: Vegið meðaltal (Rauð heil lína)
                    fig.add_scatter(x=df_saman['Dagsetning_str'], y=df_saman['Vegið meðalverð'], 
                                    mode='lines+markers', name='Vegið meðaltal', 
                                    line=dict(color='red', width=3))
                    
                    fig.update_yaxes(rangemode="tozero")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Allt uppselt hjá öllum völdum hótelum á þessu tímabili!")
        else:
            st.error("Þú þarft að bæta við að minnsta kosti einum gististað vinstra megin áður en þú leitar!")

if __name__ == "__main__":
    main()
