import streamlit as st
import pandas as pd
import unicodedata

st.set_page_config(page_title="Sales & Ops Performance", layout="wide")

def normalize_name(name):
    """Supprime les accents, met en minuscule et nettoie les espaces."""
    if pd.isna(name):
        return ""
    # Normalisation Unicode pour enlever les accents
    name = unicodedata.normalize('NFKD', str(name)).encode('ASCII', 'ignore').decode('utf-8')
    return name.lower().strip()

st.title("🚀 Dashboard de Performance Commerciale")

# 1. Upload
col1, col2, col3 = st.columns(3)
with col1:
    res_file = st.file_uploader("1. Liste Restaurants (CSV - ';')", type="csv")
with col2:
    orders_file = st.file_uploader("2. Export Commandes (CSV)", type="csv")
with col3:
    sales_file = st.file_uploader("3. Mapping Sales (Nom Resto + Sales)", type="csv")

if res_file and orders_file:
    # Lecture (Gestion du séparateur ; pour la liste officielle)
    res_df = pd.read_csv(res_file, sep=';')
    orders_df = pd.read_csv(orders_file)
    
    # Dates
    res_df['Created At'] = pd.to_datetime(res_df['Created At'], dayfirst=True, errors='coerce')
    orders_df['order day'] = pd.to_datetime(orders_df['order day'], errors='coerce')
    
    # Référence pour l'ancienneté (Dernière date du fichier commandes)
    ref_date = orders_df['order day'].max()
    res_df['Ancienneté (Jours)'] = (ref_date - res_df['Created At']).dt.days

    # Performance par Restaurant ID (Plus fiable)
    delivered = orders_df[orders_df['status'] == 'Delivered']
    perf_res = delivered.groupby('Restaurant ID').agg(
        Commandes=('order id', 'count'),
        CA_Total=('item total', 'sum')
    ).reset_index()

    # Fusion Base + Performance
    main_df = pd.merge(res_df, perf_res, left_on='Id', right_on='Restaurant ID', how='left')

    # --- MAPPING SALES AVEC TOLÉRANCE ACCENTS/CASSE ---
    sales_person_col = "Sales Name"
    if sales_file:
        sales_df = pd.read_csv(sales_file)
        
        # On cherche la colonne du nom dans le fichier Sales
        sales_name_col = sales_df.columns[0] # Par défaut la 1ère colonne
        if 'Restaurant Name' in sales_df.columns:
            sales_name_col = 'Restaurant Name'
            
        # On cherche la colonne du commercial
        if 'Sales Name' in sales_df.columns:
            sales_person_col = 'Sales Name'
        else:
            sales_person_col = sales_df.columns[1]

        # Création des clés de matching normalisées
        main_df['match_key'] = main_df['Restaurant Name'].apply(normalize_name)
        sales_df['match_key'] = sales_df[sales_name_col].apply(normalize_name)
        
        # Mapping
        sales_map = sales_df[['match_key', sales_person_col]].drop_duplicates('match_key')
        main_df = pd.merge(main_df, sales_map, on='match_key', how='left')
    
    # Nettoyage
    main_df[sales_person_col] = main_df[sales_person_col].fillna("Non Assigné")
    main_df[['Commandes', 'CA_Total']] = main_df[['Commandes', 'CA_Total']].fillna(0)

    # --- INTERFACE ONGLETS ---
    tab1, tab2 = st.tabs(["📋 Détails Restaurants", "🏆 Performance par Sales"])

    with tab1:
        st.subheader("Liste complète des restaurants")
        cols = ['Restaurant Name', 'Main City', 'Created At', 'Ancienneté (Jours)', 'Commandes', 'CA_Total', sales_person_col]
        st.dataframe(main_df[cols].sort_values(by='Created At', ascending=False), use_container_width=True)

    with tab2:
        st.subheader("Récapitulatif par Commercial")
        # Groupement par Sales
        sales_perf = main_df.groupby(sales_person_col).agg(
            Nombre_Restos=('Restaurant Name', 'count'),
            Total_Commandes=('Commandes', 'sum'),
            Total_CA=('CA_Total', 'sum')
        ).reset_index().sort_values(by='Total_CA', ascending=False)
        
        st.table(sales_perf) # Utilisation de table pour un rendu fixe et propre

    # Export pour Google Sheets
    csv = main_df[cols].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Télécharger l'export complet", data=csv, file_name='performance_globale.csv')

else:
    st.info("👋 En attente des fichiers CSV pour calculer les performances...")
