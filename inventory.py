import streamlit as st
import pandas as pd
from datetime import date
from utils import update_cash_balance
from .auth import has_permission

def show_inventory():
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'inventory'):
        st.error("You don't have permission to access this page")
        return
    
    st.header("Inventory Management")
    
    # Determine which units to show based on user's business unit
    units_to_show = []
    if user['business_unit'] in ['All', 'Unit A']:
        units_to_show.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units_to_show.append('Unit B')
    
    unit_tabs = st.tabs(units_to_show)
    
    for i, unit in enumerate(units_to_show):
        with unit_tabs[i]:
            tab1, tab2 = st.tabs(["Purchase", "Sale"])
            
            with tab1:
                record_transaction("Purchase", unit)
            with tab2:
                record_transaction("Sale", unit)

def record_transaction(transaction_type, business_unit):
    with st.form(f"{transaction_type.lower()}_form_{business_unit}", clear_on_submit=True):
        st.subheader(f"New {transaction_type} - {business_unit}")
        cols = st.columns(2)
        with cols[0]:
            date_transaction = st.date_input("Date", value=date.today())
            quantity_kg = st.number_input("Quantity (kg)", min_value=0.0, step=0.001, format="%.3f")
        with cols[1]:
            unit_price = st.number_input("Price per kg (AED)", min_value=0.0, step=0.01)
            remarks = st.text_input("Supplier" if transaction_type == "Purchase" else "Customer")
        
        total_amount = quantity_kg * unit_price
        st.write(f"Total Amount: AED {total_amount:,.2f}")
        
        if st.form_submit_button(f"Record {transaction_type}"):
            new_entry = pd.DataFrame([{
                'Date': date_transaction,
                'Transaction Type': transaction_type,
                'Quantity_kg': quantity_kg,
                'Unit Price': unit_price,
                'Total Amount': total_amount,
                'Remarks': remarks,
                'Business Unit': business_unit
            }])
            st.session_state.inventory = pd.concat([st.session_state.inventory, new_entry], ignore_index=True)
            
            if transaction_type == "Purchase":
                update_cash_balance(total_amount, business_unit, 'subtract')
            elif transaction_type == "Sale":
                update_cash_balance(total_amount, business_unit, 'add')
            
            st.success(f"{transaction_type} recorded!")