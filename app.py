import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="Performance Sales", layout="wide")

def clean_string(text):
    """Normalisation totale pour le matching (enlève accents, espaces, majuscules)."""
    if pd.isna(text):
        return ""
    # Enlever les accents
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')
    # Garder uniquement lettres et chiffres
    text = re.sub(r'[^a-zA-Z0-9]', '', text).lower()
    return text.strip()

st.title("📊 Dashboard Performance & Sales")

# --- 1. CHARGEMENT DES FICHIERS ---
st.sidebar.header("📁 Import des fichiers")
res_file = st.sidebar.file_uploader("1. Restaurant List (CSV ;)", type="csv")
orders_file = st.sidebar.file_uploader("2. Export Commandes (CSV)", type="csv")
sales_file = st.sidebar.file_uploader("3. Fichier Sales (Creation par sales)", type="csv")

if res_file and orders_file:
    # Lecture des fichiers principaux
    res_df = pd.read_csv(res_file, sep=';')
    orders_df = pd.read_csv(orders_file)
    
    # Dates
    res_df['Created At'] = pd.to_datetime(res_df['Created At'], dayfirst=True, errors='coerce')
    orders_df['order day'] = pd.to_datetime(orders_df['order day'], errors='coerce')
    
    # Référence pour l'ancienneté
    ref_date = orders_df['order day'].max()
    res_df['Ancienneté (Jours)'] = (ref_date - res_df['Created At']).dt.days

    # Performance
    delivered = orders_df[orders_df['status'] == 'Delivered']
    perf_res = delivered.groupby('Restaurant ID').agg(
        Commandes=('order id', 'count'),
        CA_Total=('item total', 'sum')
    ).reset_index()

    main_df = pd.merge(res_df, perf_res, left_on='Id', right_on='Restaurant ID', how='left')
    main_df[['Commandes', 'CA_Total']] = main_df[['Commandes', 'CA_Total']].fillna(0)

    # --- 2. MAPPING SALES (CORRECTIF NOM DU COMMERCIAL) ---
    nom_comm_col = "Nom du commercial"
    
    if sales_file:
        sales_df = pd.read_csv(sales_file)
        
        # Mapping spécifique selon tes colonnes : "Sales Rep" et "Nom de l'établissement"
        # On crée les clés de matching propres
        main_df['match_key'] = main_df['Restaurant Name'].apply(clean_string)
        sales_df['match_key'] = sales_df["Nom de l'établissement"].apply(clean_string)
        
        # On prépare le dictionnaire de correspondance
        sales_map = sales_df[['match_key', 'Sales Rep']].drop_duplicates('match_key')
        
        # Fusion
        main_df = pd.merge(main_df, sales_map, on='match_key', how='left')
        main_df = main_df.rename(columns={'Sales Rep': nom_comm_col})
    else:
        main_df[nom_comm_col] = "Non Assigné"

    main_df[nom_comm_col] = main_df[nom_comm_col].fillna("Non Assigné")

    # --- 3. FILTRE DE DATE ---
    st.sidebar.markdown("---")
    min_d = res_df['Created At'].min()
    max_d = res_df['Created At'].max()
    
    start_date, end_date = st.sidebar.date_input(
        "Filtrer par date de création :",
        value=(pd.to_datetime("2025-12-01"), pd.to_datetime("2026-01-31")),
        min_value=min_d,
        max_value=max_d
    )

    filtered_df = main_df[
        (main_df['Created At'] >= pd.to_datetime(start_date)) & 
        (main_df['Created At'] <= pd.to_datetime(end_date))
    ]

    # --- 4. AFFICHAGE DES ONGLETS ---
    tab1, tab2 = st.tabs(["📋 Détails Restaurants", "🏆 Performance par Commercial"])

    with tab1:
        st.subheader(f"Restaurants créés entre {start_date} et {end_date}")
        disp_cols = ['Restaurant Name', 'Main City', 'Created At', 'Ancienneté (Jours)', 'Commandes', 'CA_Total', nom_comm_col]
        st.dataframe(filtered_df[disp_cols].sort_values(by='Commandes', ascending=False), use_container_width=True)

    with tab2:
        st.subheader("Classement des Commerciaux (Basé sur le filtre de date)")
        agg_sales = filtered_df.groupby(nom_comm_col).agg(
            Restos_Signés=('Restaurant Name', 'count'),
            Total_Commandes=('Commandes', 'sum'),
            CA_Généré=('CA_Total', 'sum')
        ).reset_index().sort_values(by='CA_Généré', ascending=False)
        
        st.dataframe(agg_sales, use_container_width=True)

    # Export
    csv = filtered_df[disp_cols].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Télécharger l'export Sheets", data=csv, file_name='performance_sales_final.csv')

else:
    st.info("Veuillez charger les 3 fichiers CSV pour lancer l'analyse.")
