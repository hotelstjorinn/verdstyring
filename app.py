import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import datetime

st.set_page_config(page_title="Hótelstjórinn markaðsverð", layout="wide")

# ==========================================
# GERVIGÖGN TIL AÐ PRÓFA VIÐMÓTIÐ
def saekja_gervigogn(hotel_listi, fjoldi_daga):
    idag = datetime.date.today()
    gogn = []
    # Keyrir í gegnum ÖLL hótelin sem þú ert búinn að velja
    for hotel in hotel_listi:
        for i in range(fjoldi_daga):
            dagur = idag + datetime.timedelta(days=i)
            verd = np.random.choice([0, 24846, 32638, 15000, 28000]) 
            gogn.append({"Dagsetning": dagur, "Hótel": hotel, "Verð (ISK)": verd})
    return pd.DataFrame(gogn)
# ==========================================

def main():
    st.title("🏨 Hótelstjórinn markaðsverð")

    # --- BÚUM TIL MINNI TIL AÐ GEYMA MÖRG HÓTEL ---
    if 'valin_hotel' not in st.session_state:
        st.session_state['valin_hotel'] = []

    # --- HLIÐARSTIKA (LEIT OG LISTI) ---
    st.sidebar.header("Leit")
    
    # Textaboxið - hér slærðu inn og ýtir á Enter
    nytt_hotel = st.sidebar.text_input("Bæta við gististað (ýttu á Enter)")
    
    # Ef þú slóst eitthvað inn og ýttir á Enter, bætum við því á listann!
    if nytt_hotel and nytt_hotel not in st.session_state['valin_hotel']:
        st.session_state['valin_hotel'].append(nytt_hotel)

    # Sýnum öll hótelin sem þú ert búinn að safna upp
    if len(st.session_state['valin_hotel']) > 0:
        st.sidebar.markdown("### Valdir gististaðir:")
        for i, hotel in enumerate(st.session_state['valin_hotel']):
            st.sidebar.markdown(f"- **{hotel}**")
            
        # Takki til að hreinsa út og byrja upp á nýtt ef þú vilt breyta
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
        # Pössum að það sé allavega eitt hótel á listanum fyrst
        if len(st.session_state['valin_hotel']) > 0:
            st.success(f"Sæki gögn fyrir **{len(st.session_state['valin_hotel'])}** gististaði í **{dagar_valdir}** daga. Bíddu andartak...")
            
            # ⚠️ HÉR KEMUR ÞINN ALVÖRU KÓÐI ⚠️
            # (Hann mun taka við listanum af hótelum og sækja gögn fyrir þau öll)
            df = saekja_gervigogn(st.session_state['valin_hotel'], dagar_valdir) 

            # --- VINNSLA Á GÖGNUM TIL SÝNINGAR ---
            if not df.empty:
                df['Staða'] = np.where(df['Verð (ISK)'] > 0, 'Laust', 'Uppselt')
                df['Verð (ISK)'] = pd.to_numeric(df['Verð (ISK)'], errors='coerce').fillna(0).astype(int)
                df['Verð sýnt'] = df['Verð (ISK)'].apply(lambda x: f"{x:,}".replace(",", ".") if x > 0 else "")

                df['Dagsetning_str'] = pd.to_datetime(df['Dagsetning']).dt.strftime("%d.%m")
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
                    
                    fig.update_yaxes(rangemode="tozero")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Allt uppselt hjá öllum völdum hótelum á þessu tímabili!")
        else:
            # Ef maður ýtir á 1/7/30 daga takka en hefur ekki sett nein hótel inn
            st.error("Þú þarft að bæta við að minnsta kosti einum gististað vinstra megin áður en þú leitar!")

if __name__ == "__main__":
    main()
