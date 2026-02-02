import streamlit as st
import pandas as pd
import unicodedata
import re
from datetime import datetime

st.set_page_config(page_title="Performance & Volume Horaires", layout="wide")

def clean_string(text):
    """Normalisation totale : enlève accents, majuscules, et caractères spéciaux."""
    if pd.isna(text):
        return ""
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-zA-Z0-9]', '', text).lower()
    return text.strip()

def calculate_hours(start_str, end_str):
    """Calcule l'amplitude horaire quotidienne en heures décimales."""
    try:
        fmt = '%H:%M:%S'
        start = datetime.strptime(str(start_str), fmt)
        end = datetime.strptime(str(end_str), fmt)
        delta = (end - start).total_seconds() / 3600
        if delta < 0: # Cas des restaurants fermant après minuit
            delta += 24
        return round(delta, 2)
    except:
        return 0.0

st.title("📊 Dashboard Performance, Sales & Volume Horaires")

# --- 1. CHARGEMENT DES FICHIERS ---
st.sidebar.header("📁 Import des données")
res_file = st.sidebar.file_uploader("1. Restaurant List (CSV ;)", type="csv")
orders_file = st.sidebar.file_uploader("2. Export Commandes (CSV)", type="csv")
sales_file = st.sidebar.file_uploader("3. Fichier Sales (Creation par sales)", type="csv")

if res_file and orders_file:
    res_df = pd.read_csv(res_file, sep=';')
    orders_df = pd.read_csv(orders_file)
    
    # Conversion Dates
    res_df['Created At'] = pd.to_datetime(res_df['Created At'], dayfirst=True, errors='coerce')
    orders_df['order day'] = pd.to_datetime(orders_df['order day'], errors='coerce')
    
    # --- 2. CALCULS HORAIRES ET ANCIENNETÉ ---
    ref_date = orders_df['order day'].max()
    res_df['Ancienneté (Jours)'] = (ref_date - res_df['Created At']).dt.days
    res_df['Ancienneté (Jours)'] = res_df['Ancienneté (Jours)'].apply(lambda x: max(x, 0))

    # Amplitude quotidienne (Heures/Jour)
    res_df['Heures/Jour'] = res_df.apply(lambda x: calculate_hours(x['Starting Time'], x['Closing Time']), axis=1)
    
    # Volume Total Heures (Amplitude * Nombre de jours depuis création)
    res_df['Volume Horaires Total'] = (res_df['Heures/Jour'] * res_df['Ancienneté (Jours)']).round(1)

    # --- 3. PERFORMANCE VENTES ---
    delivered = orders_df[orders_df['status'] == 'Delivered']
    perf_res = delivered.groupby('Restaurant ID').agg(
        Commandes=('order id', 'count'),
        CA_Total=('item total', 'sum')
    ).reset_index()

    main_df = pd.merge(res_df, perf_res, left_on='Id', right_on='Restaurant ID', how='left')
    main_df[['Commandes', 'CA_Total']] = main_df[['Commandes', 'CA_Total']].fillna(0)

    # --- 4. MAPPING SALES (AVEC NORMALISATION NOM COMMERCIAL) ---
    nom_comm_col = "Nom du commercial"
    if sales_file:
        sales_df = pd.read_csv(sales_file)
        main_df['match_key'] = main_df['Restaurant Name'].apply(clean_string)
        sales_df['match_key'] = sales_df["Nom de l'établissement"].apply(clean_string)
        
        # Unification du nom du commercial (Majuscule au début, pas d'espaces inutiles)
        sales_df[nom_comm_col] = sales_df['Sales Rep'].str.strip().str.title()
        
        sales_map = sales_df[['match_key', nom_comm_col]].drop_duplicates('match_key')
        main_df = pd.merge(main_df, sales_map, on='match_key', how='left')
    else:
        main_df[nom_comm_col] = "Non Assigné"

    main_df[nom_comm_col] = main_df[nom_comm_col].fillna("Non Assigné")

    # --- 5. FILTRES ---
    st.sidebar.markdown("---")
    st.sidebar.header("🎯 Filtres")
    start_d, end_d = st.sidebar.date_input("Période de création :", [pd.to_datetime("2025-12-01"), pd.to_datetime("2026-01-31")])
    
    liste_sales = ["Tous"] + sorted(main_df[nom_comm_col].unique().tolist())
    selected_sales = st.sidebar.selectbox("Filtrer par Commercial :", liste_sales)

    # Application des filtres
    filtered_df = main_df[
        (main_df['Created At'] >= pd.to_datetime(start_d)) & 
        (main_df['Created At'] <= pd.to_datetime(end_d))
    ].copy()
    
    if selected_sales != "Tous":
        filtered_df = filtered_df[filtered_df[nom_comm_col] == selected_sales]

    # --- 6. AFFICHAGE ---
    tab1, tab2 = st.tabs(["📋 Détails Restaurants", "🏆 Performance par Sales"])

    with tab1:
        st.subheader("Détails et Disponibilité")
        disp_cols = [
            'Restaurant Name', 'Created At', 'Ancienneté (Jours)', 
            'Heures/Jour', 'Volume Horaires Total', 'Commandes', 'CA_Total', nom_comm_col
        ]
        st.dataframe(filtered_df[disp_cols].sort_values(by='Volume Horaires Total', ascending=False), use_container_width=True)

    with tab2:
        st.subheader("Résumé par Commercial")
        # Le résumé se base sur la période de création sélectionnée
        res_sales = filtered_df.groupby(nom_comm_col).agg(
            Restos_Signés=('Restaurant Name', 'count'),
            Volume_Horaires_Cumulé=('Volume Horaires Total', 'sum'),
            Total_Commandes=('Commandes', 'sum'),
            CA_Généré=('CA_Total', 'sum')
        ).reset_index().sort_values(by='CA_Généré', ascending=False)
        
        st.dataframe(res_sales, use_container_width=True)

    # Export
    csv = filtered_df[disp_cols].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Télécharger l'export complet", data=csv, file_name='performance_volume_horaire.csv')

else:
    st.info("Veuillez charger les fichiers pour générer le dashboard.")
