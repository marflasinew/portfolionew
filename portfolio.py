#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

st.set_page_config(layout="wide")

EXCEL_FILE = "portfel_inwestycje.xlsx"

@st.cache_data
def generate_cashflow(df, months=6):
    df = df.copy()
    df['Data wykupu'] = pd.to_datetime(df['Data wykupu'], errors='coerce')
    today = pd.to_datetime(datetime.today().date())
    future_months = [today + pd.DateOffset(months=i) for i in range(months + 1)]
    cashflow = pd.DataFrame({'Miesiąc': [d.strftime('%Y-%m') for d in future_months]})
    cashflow['Gotówka'] = 0.0
    cashflow['Instrumenty'] = ""
    for _, row in df.iterrows():
        wykup = row['Data wykupu']
        if pd.notna(wykup) and wykup > today:
            miesiac = wykup.strftime('%Y-%m')
            zwrot = row['Kwota końcowa']
            if pd.isna(zwrot):
                if pd.notna(row['Kwota bieżąca']):
                    zwrot = row['Kwota bieżąca']
                elif pd.notna(row['Kwota (PLN)']) and pd.notna(row['Oprocentowanie (%)']):
                    zwrot = row['Kwota (PLN)'] * (1 + row['Oprocentowanie (%)'] / 100)
            cashflow.loc[cashflow['Miesiąc'] == miesiac, 'Gotówka'] += zwrot
            cashflow.loc[cashflow['Miesiąc'] == miesiac, 'Instrumenty'] += f"{row['Instrument']} ({zwrot:.2f})\n"
    return cashflow

# ✅ Wczytaj dane z pliku (jeśli istnieje) i zapisz do sesji
if 'inwestycje' not in st.session_state:
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        for col in ['Data zakupu', 'Data wykupu', 'Data wyceny']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        st.session_state['inwestycje'] = df
    else:
        st.session_state['inwestycje'] = pd.DataFrame(columns=[
            'Typ aktywa', 'Instrument', 'Emitent', 'Waluta', 'Kwota (PLN)',
            'Data zakupu', 'Data wykupu', 'Oprocentowanie (%)',
            'Kwota bieżąca', 'Data wyceny', 'Kwota końcowa', 'Zysk / Strata'
        ])

st.title("Automatyczny Dashboard Portfela Inwestycyjnego")

with st.sidebar:
    st.header("Dodaj nową inwestycję")
    typ = st.selectbox("Typ aktywa", ["Obligacja", "Lokata", "ETF"])
    instr = st.text_input("Nazwa instrumentu")
    emitent = st.text_input("Emitent / Instytucja")
    waluta = st.selectbox("Waluta", ["PLN", "EUR", "USD"])
    kwota = st.number_input("Kwota inwestycji (PLN)", value=10000.00, step=1000.0)
    data_zakupu = st.date_input("Data zakupu", value=datetime.today())
    data_wykupu = st.date_input("Data wykupu / sprzedaży")
    oprocent = st.number_input("Oprocentowanie (%)", value=5.0, step=0.1)
    kwota_biezaca = st.number_input("Kwota bieżąca (PLN)", value=0.0, step=1000.0)
    data_wyceny = st.date_input("Data wyceny", value=datetime.today())

    if st.button("Dodaj do portfela"):
        nowa = {
            'Typ aktywa': typ,
            'Instrument': instr,
            'Emitent': emitent,
            'Waluta': waluta,
            'Kwota (PLN)': kwota,
            'Data zakupu': pd.to_datetime(data_zakupu),
            'Data wykupu': pd.to_datetime(data_wykupu),
            'Oprocentowanie (%)': oprocent,
            'Kwota bieżąca': kwota_biezaca if kwota_biezaca > 0 else None,
            'Data wyceny': pd.to_datetime(data_wyceny),
            'Kwota końcowa': None,
            'Zysk / Strata': None
        }
        st.session_state['inwestycje'] = pd.concat(
            [st.session_state['inwestycje'], pd.DataFrame([nowa])],
            ignore_index=True
        )
        st.success("Inwestycja została dodana")

# 🧾 Dane inwestycji
df = st.session_state['inwestycje']
for col in ['Data zakupu', 'Data wykupu', 'Data wyceny']:
    df[col] = pd.to_datetime(df[col], errors='coerce')

# 🎯 Obliczenia końcowe
df['Kwota końcowa'] = df.apply(
    lambda row: row['Kwota końcowa'] if pd.notna(row['Kwota końcowa']) else
                row['Kwota bieżąca'] if pd.notna(row['Kwota bieżąca']) else
                row['Kwota (PLN)'] * (1 + row['Oprocentowanie (%)'] / 100)
                if pd.notna(row['Kwota (PLN)']) and pd.notna(row['Oprocentowanie (%)']) else None,
    axis=1
)
df['Zysk / Strata'] = df.apply(
    lambda row: round(row['Kwota końcowa'] - row['Kwota (PLN)'], 2)
    if pd.notna(row['Kwota końcowa']) and pd.notna(row['Kwota (PLN)']) else None,
    axis=1
)

# ✏️ Tabela edytowalna
st.subheader("Aktualny portfel inwestycyjny")
edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

# 📊 Podsumowanie
st.subheader("Podsumowanie portfela")
total_invested = edited_df['Kwota (PLN)'].sum()
total_final = edited_df['Kwota końcowa'].sum()
total_profit = total_final - total_invested if not pd.isna(total_final) else None

st.metric("Zainwestowana kwota", f"{total_invested:,.2f} PLN")
if not pd.isna(total_profit):
    st.metric("Zysk / Strata (łącznie)", f"{total_profit:,.2f} PLN")

# 🧮 Wykres udziałów
fig, ax = plt.subplots()
kategorie = edited_df.groupby('Typ aktywa')['Kwota (PLN)'].sum()
ax.pie(kategorie, labels=kategorie.index, autopct='%1.1f%%')
ax.axis('equal')
st.pyplot(fig)

# 🔁 Przyszłe przepływy gotówkowe
st.subheader("Przyszłe przepływy gotówkowe (6 miesięcy)")
cashflow_df = generate_cashflow(edited_df)
st.dataframe(cashflow_df, use_container_width=True)

# 📈 Tabela zysków
st.subheader("Zysk / Strata dla każdej inwestycji")
st.dataframe(edited_df[['Instrument', 'Kwota (PLN)', 'Kwota bieżąca', 'Kwota końcowa', 'Zysk / Strata', 'Data wykupu']], use_container_width=True)

# 💾 Zapis do Excela
edited_df.to_excel(EXCEL_FILE, index=False)
st.success("Zapisano dane do pliku Excel: portfel_inwestycje.xlsx")
st.session_state['inwestycje'] = edited_df


# In[11]:


import pandas as pd

# Wczytanie pliku
df = pd.read_excel("portfel_inwestycje.xlsx")

# Wyświetlenie pierwszych 5 wierszy
print(df.head())


# In[ ]:



