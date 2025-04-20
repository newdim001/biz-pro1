import streamlit as st
import pandas as pd
from datetime import date
from utils import update_cash_balance  # Ensure this function supports 'simulate' mode
from .auth import has_permission

# Utility function to update cash balance
def update_cash_balance(amount, business_unit, action, simulate=False):
    """
    Updates or simulates the cash balance for a business unit.
    
    Parameters:
        amount (float): The amount to add/subtract.
        business_unit (str): The business unit ('Unit A', 'Unit B', etc.).
        action (str): 'add' or 'subtract'.
        simulate (bool): If True, only checks if the action is possible without modifying the balance.
    
    Returns:
        bool: True if the action is possible, False otherwise.
    """
    # Initialize cash balance if not present
    if 'cash_balance' not in st.session_state:
        st.session_state.cash_balance = {'Unit A': 10000.0, 'Unit B': 10000.0}  # Example initial balances
    
    current_balance = st.session_state.cash_balance.get(business_unit, 0.0)
    
    if action == 'subtract':
        if current_balance < amount:
            return False  # Insufficient balance
        if not simulate:
            st.session_state.cash_balance[business_unit] -= amount
    elif action == 'add':
        if not simulate:
            st.session_state.cash_balance[business_unit] += amount
    
    return True  # Action is possible

# Inventory Management Page
def show_inventory():
    # Access control
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'inventory'):
        st.error("You don't have permission to access this page")
        return
    
    # Initialize inventory if not already present
    if 'inventory' not in st.session_state:
        st.session_state.inventory = pd.DataFrame(columns=[
            'Date', 'Transaction Type', 'Quantity_kg', 'Unit Price', 'Total Amount', 'Remarks', 'Business Unit'
        ])
    
    st.header("Inventory Management")
    units_to_show = ['Unit A', 'Unit B'] if user['business_unit'] == 'All' else [user['business_unit']]
    unit_tabs = st.tabs(units_to_show)
    
    for i, unit in enumerate(units_to_show):
        with unit_tabs[i]:
            tab1, tab2 = st.tabs(["Purchase", "Sale"])
            
            with tab1:
                record_transaction("Purchase", unit)
            with tab2:
                record_transaction("Sale", unit)

# Record Transaction Function
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
            # Input validation
            if quantity_kg <= 0 or unit_price <= 0:
                st.error("Quantity and price must be greater than zero.")
                return
            
            # Handle purchase transactions
            if transaction_type == "Purchase":
                # Check if cash balance is sufficient
                cash_sufficient = update_cash_balance(total_amount, business_unit, 'subtract', simulate=True)
                if not cash_sufficient:
                    st.error("Insufficient cash balance to complete the purchase.")
                    return  # Exit without recording the transaction
                
                # Update cash balance
                update_cash_balance(total_amount, business_unit, 'subtract')
            
            # Handle sale transactions
            elif transaction_type == "Sale":
                # Update cash balance
                update_cash_balance(total_amount, business_unit, 'add')
            
            # Record the transaction in inventory
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
            
            st.success(f"{transaction_type} recorded!")