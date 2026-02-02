import streamlit as st
import pandas as pd

st.set_page_config(page_title="Performance Nouveaux Restaurants", layout="wide")

st.title("📊 Analyse des Nouveaux Restaurants")
st.write("Comparez la liste des restaurants avec les ventes réelles.")

# 1. Upload des fichiers
col1, col2 = st.columns(2)
with col1:
    res_file = st.file_uploader("Fichier 'restaurant-list'", type="csv")
with col2:
    orders_file = st.file_uploader("Fichier 'admin-earnings-orders'", type="csv")

if res_file and orders_file:
    # Lecture des données
    # Note: On utilise le séparateur ';' pour la liste des restos comme vu dans ton fichier
    res_df = pd.read_csv(res_file, sep=';')
    orders_df = pd.read_csv(orders_file)

    # Nettoyage des dates
    res_df['Created At'] = pd.to_datetime(res_df['Created At'], dayfirst=True, errors='coerce')
    
    # 2. Filtres latéraux
    st.sidebar.header("Filtres")
    start_date = st.sidebar.date_input("Date de début", value=pd.to_datetime("2025-12-01"))
    end_date = st.sidebar.date_input("Date de fin", value=pd.to_datetime("2026-01-31"))

    # Filtrage des restaurants
    mask = (res_df['Created At'] >= pd.to_datetime(start_date)) & (res_df['Created At'] <= pd.to_datetime(end_date))
    new_res = res_df.loc[mask].copy()

    # 3. Calcul des performances
    # On ne garde que les commandes livrées
    delivered = orders_df[orders_df['status'] == 'Delivered']
    
    perf = delivered.groupby('Restaurant ID').agg(
        Commandes=('order id', 'count'),
        CA_Total=('item total', 'sum'),
        Commissions=('restaurant commission', 'sum')
    ).reset_index()

    # Fusion des données
    final_df = pd.merge(new_res, perf, left_on='Id', right_on='Restaurant ID', how='left')
    
    # Nettoyage final
    final_df = final_df[[
        'Restaurant Name', 'Main City', 'Created At', 'Status', 'Store type',
        'Commandes', 'CA_Total', 'Commissions'
    ]].fillna(0)
    
    final_df = final_df.sort_values(by='Commandes', ascending=False)

    # 4. Affichage
    st.subheader(f"Résultats : {len(final_df)} restaurants créés")
    st.dataframe(final_df, use_container_width=True)

    # 5. Export Google Sheets (CSV)
    csv = final_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Télécharger pour Google Sheets",
        data=csv,
        file_name='performance_nouveaux_restos.csv',
        mime='text/csv',
    )
else:
    st.info("Veuillez uploader les deux fichiers CSV pour commencer l'analyse.")
