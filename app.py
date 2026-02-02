import streamlit as st
import pandas as pd
import unicodedata
import re

st.set_page_config(page_title="Performance Sales & Ops", layout="wide")

def clean_string(text):
    """Nettoyage extrême : pas d'accents, pas de majuscules, pas de caractères spéciaux."""
    if pd.isna(text):
        return ""
    # Enlever les accents
    text = unicodedata.normalize('NFKD', str(text)).encode('ASCII', 'ignore').decode('utf-8')
    # Garder uniquement lettres et chiffres, en minuscule
    text = re.sub(r'[^a-zA-Z0-0]', '', text).lower()
    return text.strip()

st.title("🚀 Dashboard de Performance par Commercial")

# --- 1. UPLOAD ---
col1, col2, col3 = st.columns(3)
with col1:
    res_file = st.file_uploader("1. Fichier Restaurant List (CSV ;)", type="csv")
with col2:
    orders_file = st.file_uploader("2. Fichier Commandes (CSV)", type="csv")
with col3:
    sales_file = st.file_uploader("3. Fichier Mapping Commerciaux (CSV)", type="csv")

if res_file and orders_file:
    # Lecture des fichiers
    res_df = pd.read_csv(res_file, sep=';')
    orders_df = pd.read_csv(orders_file)
    
    # Dates
    res_df['Created At'] = pd.to_datetime(res_df['Created At'], dayfirst=True, errors='coerce')
    orders_df['order day'] = pd.to_datetime(orders_df['order day'], errors='coerce')
    
    # Calcul de l'ancienneté (Date max du fichier de ventes)
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

    # --- 2. MAPPING COMMERCIAL (SALES) ---
    col_commercial = "Nom du commercial"
    if sales_file:
        sales_df = pd.read_csv(sales_file)
        
        # Identification des colonnes dans le fichier Sales
        # On suppose Col 1 = Nom Resto, Col 2 = Nom du commercial
        s_resto_col = sales_df.columns[0]
        s_comm_col = sales_df.columns[1]

        # Création des clés de nettoyage pour le matching
        main_df['match_key'] = main_df['Restaurant Name'].apply(clean_string)
        sales_df['match_key'] = sales_df[s_resto_col].apply(clean_string)
        
        # Fusion
        sales_map = sales_df[['match_key', s_comm_col]].drop_duplicates('match_key')
        main_df = pd.merge(main_df, sales_map, on='match_key', how='left')
        main_df = main_df.rename(columns={s_comm_col: col_commercial})
    else:
        main_df[col_commercial] = "Non Assigné"

    # Nettoyage final des chiffres
    main_df[['Commandes', 'CA_Total']] = main_df[['Commandes', 'CA_Total']].fillna(0)
    main_df[col_commercial] = main_df[col_commercial].fillna("Non Assigné")

    # --- 3. AFFICHAGE ---
    tab1, tab2 = st.tabs(["📋 Détails par Restaurant", "🏆 Résumé par Commercial"])

    with tab1:
        st.subheader("Listing complet")
        # Filtre par date sur l'interface
        start_filter = st.date_input("Afficher les restos créés depuis :", value=pd.to_datetime("2025-12-01"))
        mask = main_df['Created At'] >= pd.to_datetime(start_filter)
        
        display_cols = ['Restaurant Name', 'Main City', 'Created At', 'Ancienneté (Jours)', 'Commandes', 'CA_Total', col_commercial]
        st.dataframe(main_df.loc[mask, display_cols].sort_values(by='Created At', ascending=False), use_container_width=True)

    with tab2:
        st.subheader("Classement des Commerciaux")
        # On groupe par le nom du commercial
        agg_sales = main_df.groupby(col_commercial).agg(
            Nombre_de_Restos=('Restaurant Name', 'count'),
            Total_Commandes=('Commandes', 'sum'),
            Chiffre_d_Affaire_Total=('CA_Total', 'sum')
        ).reset_index().sort_values(by='Chiffre_d_Affaire_Total', ascending=False)
        
        st.dataframe(agg_sales, use_container_width=True)

    # Export
    csv = main_df[display_cols].to_csv(index=False).encode('utf-8')
    st.download_button("📥 Télécharger pour Google Sheets", data=csv, file_name='rapport_final_performance.csv')

else:
    st.info("Veuillez charger les fichiers pour activer le dashboard.")
