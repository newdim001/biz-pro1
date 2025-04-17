import streamlit as st
import pandas as pd
from datetime import date
from utils import update_cash_balance, distribute_investment
from .auth import has_permission

def show_investments():
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'investments'):
        st.error("You don't have permission to access this page")
        return
    
    st.header("Investment Records")
    
    # Determine which units to show based on user's business unit
    units_to_show = []
    if user['business_unit'] in ['All', 'Unit A']:
        units_to_show.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units_to_show.append('Unit B')
    
    unit_tabs = st.tabs(units_to_show)
    
    for i, unit in enumerate(units_to_show):
        with unit_tabs[i]:
            with st.form(f"investment_form_{unit}", clear_on_submit=True):
                st.subheader(f"Add Investment - {unit}")
                cols = st.columns(2)
                with cols[0]:
                    inv_date = st.date_input("Date", value=date.today())
                    amount = st.number_input("Amount (AED)", min_value=0.0, step=0.01)
                with cols[1]:
                    investor = st.text_input("Investor Name")
                    remarks = st.text_input("Purpose")
                
                if st.form_submit_button(f"Add Investment to {unit}"):
                    new_investment = pd.DataFrame([{
                        'Date': inv_date,
                        'Amount': amount,
                        'Investor': investor,
                        'Remarks': remarks,
                        'Business Unit': unit
                    }])
                    st.session_state.investments = pd.concat([st.session_state.investments, new_investment], ignore_index=True)
                    update_cash_balance(amount, unit, 'add')
                    
                    # Distribute investment to partners
                    if distribute_investment(unit, amount, investor):
                        st.success(f"Investment added and distributed to partners in {unit}!")
                    else:
                        st.success(f"Investment added to {unit} (no partners to distribute to)")