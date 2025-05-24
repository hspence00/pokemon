import streamlit as st
import pandas as pd
import requests
from io import StringIO
CSV_URL = "https://www.pricecharting.com/price-guide/download-custom?t=94f0ecf697966284ee918a0cff2297df49c48191&category=pokemon-cards"

def load_data_wrapper():
    return load_data().copy()

@st.cache(allow_output_mutation=True)
def load_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(CSV_URL, headers=headers)
    if response.status_code != 200:
        return pd.DataFrame()

    csv_text = response.content.decode("utf-8")
    df = pd.read_csv(StringIO(csv_text))
    df.rename(columns=lambda x: x.strip(), inplace=True)

    df = df[~df['product-name'].str.lower().str.contains("box|pack", na=False)]

    df['Raw Price'] = pd.to_numeric(df['loose-price'].str.replace("$", "").str.replace(",", ""), errors='coerce')
    df['PSA 9 Price'] = pd.to_numeric(df['graded-price'].str.replace("$", "").str.replace(",", ""), errors='coerce')
    df['PSA 10 Price'] = pd.to_numeric(df['manual-only-price'].str.replace("$", "").str.replace(",", ""), errors='coerce')

    df = df[df['PSA 10 Price'] > 0]

    df = df.rename(columns={
        'product-name': 'Card Name',
        'console-name': 'Set Name',
        'release-date': 'Release Date'
    })

    df['Release Date'] = pd.to_datetime(df['Release Date'], errors='coerce')
    df = df.dropna(subset=['Release Date'])

    df['Release Year'] = df['Release Date'].dt.year
    return df[['Card Name', 'Set Name', 'Raw Price', 'PSA 9 Price', 'PSA 10 Price', 'Release Year']]

def calculate_expected_value(row, grading_fee):
    p_10 = 0.35
    p_9 = 0.60
    return (p_10 * row['PSA 10 Price']) + (p_9 * row['PSA 9 Price']) - row['Raw Price'] - grading_fee

def show_top_150():
    st.title("Top 150 Pokémon Cards PSA 10 Price")
    st.markdown("Cards with the **highest PSA 10 value** from PriceCharting. Boxes and packs excluded.")
    df = load_data_wrapper()
    if df.empty:
        st.warning("No card data found.")
        return
    st.dataframe(df.sort_values(by='PSA 10 Price', ascending=False).head(150).reset_index(drop=True), use_container_width=True)

def show_grading_finder():
    st.title("Grading Finder")
    st.markdown("Find the most profitable cards to grade based on PSA 9/10 price and expected grading outcome.")

    df = load_data_wrapper()

    if df.empty:
        st.warning("No card data available.")
        return

    with st.form("grading_form"):
        set_options = ["All Sets"] + sorted(df['Set Name'].dropna().unique())
        selected_sets = st.multiselect("Select Set(s)", set_options, default=["All Sets"])

        max_cards = st.selectbox("Number of Cards to Display", [25, 50, 75, 100, 150])
        min_raw = st.number_input("Min Raw Card Value ($)", min_value=0.0, value=0.0, step=1.0, key="min_raw_grading_finder")
        max_raw = st.number_input("Max Raw Card Value ($)", min_value=0.0, value=20.0, step=1.0, key="max_raw_grading_finder")
        grading_speed = st.radio("Grading Speed", ["Bulk ($17 / 40 Days)", "Express ($40 / 20 Days)"])

        submitted = st.form_submit_button("Find Cards")

    if submitted:
        grading_fee = 17 if "Bulk" in grading_speed else 40

        filtered_df = df[(df['Raw Price'] >= min_raw) & (df['Raw Price'] <= max_raw)]
        if "All Sets" not in selected_sets:
            filtered_df = filtered_df[filtered_df['Set Name'].isin(selected_sets)]

        filtered_df = filtered_df.copy()
        filtered_df['Expected Profit'] = filtered_df.apply(lambda row: calculate_expected_value(row, grading_fee), axis=1)
        filtered_df['ROI %'] = 100 * filtered_df['Expected Profit'] / (filtered_df['Raw Price'] + grading_fee)

        sorted_df = filtered_df.sort_values(by='ROI %', ascending=False).head(max_cards)

        st.subheader(f"Top {max_cards} Cards by Expected Profit")
        st.dataframe(sorted_df.reset_index(drop=True), use_container_width=True)

def show_grading_finder_2():
    st.title("Grading Finder 2")
    st.markdown("Analyze cards by exact release year and expected ROI.")

    df = load_data_wrapper()

    if df.empty:
        st.warning("No card data available.")
        return

    df['Year Group'] = ((2025 - df['Release Year']) // 5) * 5
    df['Year Group'] = 2025 - df['Year Group']
    df['Group Label'] = df['Year Group'].astype(str) + '–' + (df['Year Group'] - 4).astype(str)
    group_options = sorted(df['Group Label'].unique(), reverse=True)

    with st.form("grading_group_form"):
        selected_group = st.selectbox("Select 5-Year Release Group", group_options)
        max_cards = st.selectbox("Number of Cards to Display", [25, 50, 75, 100, 150])
        min_raw = st.number_input("Min Raw Card Value ($)", min_value=0.0, value=0.0, step=1.0, key="min_raw_grading_finder2")
        max_raw = st.number_input("Max Raw Card Value ($)", min_value=0.0, value=20.0, step=1.0, key="max_raw_grading_finder2")
        grading_speed = st.radio("Grading Speed", ["Bulk ($17 / 40 Days)", "Express ($40 / 20 Days)"])

        submitted = st.form_submit_button("Find Cards")

    if submitted:
        grading_fee = 17 if "Bulk" in grading_speed else 40

        filtered_df = df[(df['Group Label'] == selected_group) & (df['Raw Price'] >= min_raw) & (df['Raw Price'] <= max_raw)]

        filtered_df = filtered_df.copy()
        filtered_df['Expected Profit'] = filtered_df.apply(lambda row: calculate_expected_value(row, grading_fee), axis=1)
        filtered_df['ROI %'] = 100 * filtered_df['Expected Profit'] / (filtered_df['Raw Price'] + grading_fee)

        sorted_df = filtered_df.sort_values(by='ROI %', ascending=False).head(max_cards)

        st.subheader(f"Top {max_cards} Cards from Group: {selected_group} by Expected Profit")
        st.dataframe(sorted_df.reset_index(drop=True), use_container_width=True)

def main():
    st.set_page_config(page_title="Pokémon Grading Tool", layout="wide")
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Top 150 Pokémon Cards PSA 10 Price", "Grading Finder", "Grading Finder 2"])

    if page == "Top 150 Pokémon Cards PSA 10 Price":
        show_top_150()
    elif page == "Grading Finder":
        show_grading_finder()
    elif page == "Grading Finder 2":
        show_grading_finder_2()

if __name__ == "__main__":
    main()
