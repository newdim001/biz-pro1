import streamlit as st
import pandas as pd

def initialize_session_state():
    if 'initialized' not in st.session_state:
        st.session_state.inventory = pd.DataFrame(columns=[
            'Date', 'Transaction Type', 'Quantity_kg', 
            'Unit Price', 'Total Amount', 'Remarks', 'Business Unit'
        ])
        st.session_state.cash_balance = {'Unit A': 10000.0, 'Unit B': 10000.0}  # Use floats consistently
        st.session_state.investments = pd.DataFrame(columns=[
            'Date', 'Amount', 'Investor', 'Remarks', 'Business Unit'
        ])
        st.session_state.expenses = pd.DataFrame(columns=[
            'Date', 'Category', 'Amount', 'Description', 'Business Unit', 'Partner'
        ])
        st.session_state.partners = {
            'Unit A': pd.DataFrame(columns=['Partner', 'Share', 'Withdrawn']),
            'Unit B': pd.DataFrame(columns=['Partner', 'Share', 'Withdrawn'])
        }
        st.session_state.current_price = 100.0
        st.session_state.initialized = True