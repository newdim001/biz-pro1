import pandas as pd
import streamlit as st
from datetime import date, timedelta

def update_cash_balance(amount, business_unit, operation='add'):
    if operation == 'add':
        st.session_state.cash_balance[business_unit] += amount
    else:
        st.session_state.cash_balance[business_unit] -= amount

def calculate_inventory_value(unit):
    if 'inventory' not in st.session_state:
        return 0, 0
    unit_inv = st.session_state.inventory[st.session_state.inventory['Business Unit'] == unit]
    if unit_inv.empty: return 0, 0
    purchases = unit_inv[unit_inv['Transaction Type'] == 'Purchase']
    sales = unit_inv[unit_inv['Transaction Type'] == 'Sale']
    current_stock_kg = purchases['Quantity_kg'].sum() - sales['Quantity_kg'].sum()
    current_value = current_stock_kg * st.session_state.current_price
    return current_stock_kg, current_value

def calculate_profit_loss(unit):
    if 'inventory' not in st.session_state or 'expenses' not in st.session_state:
        return 0, 0
    unit_sales = st.session_state.inventory[
        (st.session_state.inventory['Business Unit'] == unit) &
        (st.session_state.inventory['Transaction Type'] == 'Sale')
    ]
    unit_purchases = st.session_state.inventory[
        (st.session_state.inventory['Business Unit'] == unit) &
        (st.session_state.inventory['Transaction Type'] == 'Purchase')
    ]
    unit_expenses = st.session_state.expenses[
        (st.session_state.expenses['Business Unit'] == unit) &
        (st.session_state.expenses['Category'] != 'Partner Contribution')
    ]
    gross_profit = unit_sales['Total Amount'].sum() - unit_purchases['Total Amount'].sum()
    net_profit = gross_profit - unit_expenses['Amount'].sum()
    return gross_profit, net_profit

def calculate_provisional_profit(unit):
    current_stock_kg, inventory_value = calculate_inventory_value(unit)
    investments = st.session_state.investments[
        st.session_state.investments['Business Unit'] == unit
    ]['Amount'].sum() if 'investments' in st.session_state else 0
    expenses = st.session_state.expenses[
        (st.session_state.expenses['Business Unit'] == unit) &
        (st.session_state.expenses['Category'] != 'Partner Contribution')
    ]['Amount'].sum() if 'expenses' in st.session_state else 0
    return max(0, inventory_value - investments - expenses)

def calculate_partner_profits(unit):
    if 'partners' not in st.session_state or unit not in st.session_state.partners:
        return pd.DataFrame()
    if st.session_state.partners[unit].empty:
        return pd.DataFrame()
    
    _, net_profit = calculate_profit_loss(unit)
    provisional_profit = calculate_provisional_profit(unit)
    partners_df = st.session_state.partners[unit].copy()
    
    withdrawals = st.session_state.expenses[
        (st.session_state.expenses['Business Unit'] == unit) &
        (st.session_state.expenses['Category'] == 'Partner Withdrawal')
    ].groupby('Partner')['Amount'].sum().reset_index() if 'expenses' in st.session_state else pd.DataFrame()
    
    if not withdrawals.empty:
        partners_df = partners_df.merge(withdrawals, on='Partner', how='left')
        partners_df['Amount'] = partners_df['Amount'].fillna(0)
    else:
        partners_df['Amount'] = 0
    
    partners_df['Profit_Share'] = partners_df['Share'] / 100 * net_profit
    partners_df['Provisional_Share'] = (partners_df['Share'] / 100 * provisional_profit) - partners_df['Amount']
    partners_df['Provisional_Share'] = partners_df['Provisional_Share'].apply(lambda x: max(0, x))
    partners_df['Net_Amount'] = partners_df['Profit_Share'] - partners_df['Amount']
    
    return partners_df

def calculate_combined_partner_profits():
    combined = pd.DataFrame(columns=['Partner', 'Share', 'Profit_Share', 'Provisional_Share', 'Withdrawn', 'Net_Amount'])
    for unit in ['Unit A', 'Unit B']:
        profit_df = calculate_partner_profits(unit)
        if not profit_df.empty:
            profit_df['Business Unit'] = unit
            combined = pd.concat([combined, profit_df], ignore_index=True)
    if not combined.empty:
        combined = combined.groupby('Partner').agg({
            'Share': 'sum',
            'Profit_Share': 'sum',
            'Provisional_Share': 'sum',
            'Withdrawn': 'sum',
            'Net_Amount': 'sum',
            'Business Unit': lambda x: ', '.join(x.unique())
        }).reset_index()
    return combined

def record_partner_withdrawal(unit, partner, amount, description):
    new_expense = pd.DataFrame([{
        'Date': date.today(),
        'Category': 'Partner Withdrawal',
        'Amount': amount,
        'Description': f"{description} - {partner}",
        'Business Unit': unit,
        'Partner': partner
    }])
    st.session_state.expenses = pd.concat([st.session_state.expenses, new_expense], ignore_index=True)
    update_cash_balance(amount, unit, 'subtract')

def distribute_investment(unit, amount, investor):
    if 'partners' not in st.session_state or unit not in st.session_state.partners:
        return False
    if st.session_state.partners[unit].empty:
        return False
    
    partners_df = st.session_state.partners[unit]
    total_share = partners_df['Share'].sum()
    if total_share <= 0:
        return False
    
    for _, row in partners_df.iterrows():
        partner = row['Partner']
        share = row['Share']
        partner_amount = (share / total_share) * amount
        record_partner_withdrawal(
            unit=unit,
            partner=partner,
            amount=partner_amount,
            description=f"Investment distribution from {investor}"
        )
    return True

def redistribute_shares(partners_df, freed_share):
    if partners_df.empty or partners_df['Share'].sum() <= 0:
        return partners_df
    partners_df['Share'] = partners_df['Share'] + (partners_df['Share'] / partners_df['Share'].sum() * freed_share)
    return partners_df