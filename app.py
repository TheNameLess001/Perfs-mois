import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="Performance Sales & Ops", layout="wide")

def clean_string(text):
    """Normalisation pour le matching : pas d'accents, pas de majuscules, pas de symboles."""
    if pd.isna(text):
        return ""
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'[^a-zA-Z0-9]', '', text).lower()
    return text.strip()

st.title("🚀 Dashboard Performance : Restaurants & Commerciaux")

# --- 1. CHARGEMENT DES FICHIERS ---
st.sidebar.header("📁 Chargement des données")
res_file = st.sidebar.file_uploader("1. Restaurant List (CSV ;)", type="csv")
orders_file = st.sidebar.file_uploader("2. Export Commandes (CSV)", type="csv")
sales_file = st.sidebar.file_uploader("3. Mapping Commerciaux (CSV)", type="csv")

if res_file and orders_file:
    # Lecture
    res_df = pd.read_csv(res_file, sep=';')
    orders_df = pd.read_csv(orders_file)
    
    # Conversion Dates
    res_df['Created At'] = pd.to_datetime(res_df['Created At'], dayfirst=True, errors='coerce')
    orders_df['order day'] = pd.to_datetime(orders_df['order day'], errors='coerce')
    
    # --- 2. FILTRE DE DATE DE CRÉATION (GLOBAL) ---
    st.sidebar.markdown("---")
    st.sidebar.header("🗓️ Filtre de Recrutement")
    min_date = res_df['Created At'].min()
    max_date = res_df['Created At'].max()
    
    start_date, end_date = st.sidebar.date_input(
        "Période de création des restaurants :",
        value=(pd.to_datetime("2025-12-01"), pd.to_datetime("2026-01-31")),
        min_value=min_date,
        max_value=max_date
    )

    # --- 3. CALCULS ---
    # Date de référence pour l'ancienneté
    ref_date = orders_df['order day'].max()
    res_df['Ancienneté (Jours)'] = (ref_date - res_df['Created At']).dt.days

    # Performance par Restaurant
    delivered = orders_df[orders_df['status'] == 'Delivered']
    perf_res = delivered.groupby('Restaurant ID').agg(
        Commandes=('order id', 'count'),
        CA_Total=('item total', 'sum')
    ).reset_index()

    # Fusion Base + Performance
    main_df = pd.merge(res_df, perf_res, left_on='Id', right_on='Restaurant ID', how='left')
    main_df[['Commandes', 'CA_Total']] = main_df[['Commandes', 'CA_Total']].fillna(0)

    # --- 4. MAPPING COMMERCIAL ---
    nom_comm_col = "Nom du commercial"
    if sales_file:
        sales_df = pd.read_csv(sales_file)
        s_resto_col = sales_df.columns[0]
        s_comm_col = sales_df.columns[1]

        main_df['match_key'] = main_df['Restaurant Name'].apply(clean_string)
        sales_df['match_key'] = sales_df[s_resto_col].apply(clean_string)
        
        sales_map = sales_df[['match_key', s_comm_col]].drop_duplicates('match_key')
        main_df = pd.merge(main_df, sales_map, on='match_key', how='left')
        main_df = main_df.rename(columns={s_comm_col: nom_comm_col})
    else:
        main_df[nom_comm_col] = "Non Assigné"

    main_df[nom_comm_col] = main_df[nom_comm_col].fillna("Non Assigné")

    # --- 5. APPLICATION DU FILTRE DE DATE ---
    filtered_df = main_df[
        (main_df['Created At'] >= pd.to_datetime(start_date)) & 
        (main_df['Created At'] <= pd.to_datetime(end_date))
    ]

    # --- 6. AFFICHAGE ---
    st.info(f"Analyse basée sur les restaurants créés entre le **{start_date}** et le **{end_date}**")

    tab1, tab2 = st.tabs(["📋 Détails Restaurants", "🏆 Performance par Sales"])

    with tab1:
        st.subheader("Performance individuelle")
        disp_cols = ['Restaurant Name', 'Main City', 'Created At', 'Ancienneté (Jours)', 'Commandes', 'CA_Total', nom_comm_col]
        st.dataframe(filtered_df[disp_cols].sort_values(by='Commandes', ascending=False), use_container_width=True)

    with tab2:
        st.subheader("Performance globale des Commerciaux")
        # Calcul du résumé basé sur le filtre de date
        agg_sales = filtered_df.groupby(nom_comm_col).agg(
            Restos_Signés=('Restaurant Name', 'count'),
            Total_Commandes=('Commandes', 'sum'),
            CA_Généré=('CA_Total', 'sum')
        ).reset_index().sort_values(by='CA_Généré', ascending=False)
        
        # Ajout d'une colonne % de contribution
        total_ca = agg_sales['CA_Généré'].sum()
        agg_sales['% du CA Total'] = (agg_sales['CA_Généré'] / total_ca * 100).round(2).astype(str) + '%'
        
        st.dataframe(agg_sales, use_container_width=True)

    # Export
    csv = filtered_df[disp_cols].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Télécharger cet export (Filtre appliqué)", data=csv, file_name='export_performance_filtre.csv')

else:
    st.warning("Veuillez charger vos fichiers CSV dans la barre latérale pour commencer.")
