# utils.py
import pandas as pd
import streamlit as st
from datetime import date, datetime
import numpy as np
import math
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def initialize_default_data():
    """Initialize all required session state variables with default values"""
    defaults = {
        'cash_balance': {'Unit A': 10000.0, 'Unit B': 10000.0},
        'current_price': 50.0,
        'price_history': pd.DataFrame([{
            'Date': date.today(),
            'Time': datetime.now().time(),
            'Price': 50.0
        }]),
        'inventory': pd.DataFrame(columns=[
            'Date', 'Transaction Type', 'Quantity_kg', 'Unit Price',
            'Total Amount', 'Business Unit', 'Description'
        ]),
        'expenses': pd.DataFrame(columns=[
            'Date', 'Category', 'Amount', 'Description',
            'Business Unit', 'Partner', 'Payment Method'
        ]),
        'investments': pd.DataFrame(columns=[
            'Date', 'Business Unit', 'Amount', 'Investor', 'Description'
        ]),
        'partners': {
            'Unit A': pd.DataFrame([
                {'Partner': 'Ahmed', 'Share': 60.0, 'Withdrawn': 0.0, 'Invested': 0.0},
                {'Partner': 'Fatima', 'Share': 40.0, 'Withdrawn': 0.0, 'Invested': 0.0}
            ]),
            'Unit B': pd.DataFrame([
                {'Partner': 'Ali', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0},
                {'Partner': 'Mariam', 'Share': 50.0, 'Withdrawn': 0.0, 'Invested': 0.0}
            ])
        },
        'transactions': pd.DataFrame(columns=[
            'Date', 'Type', 'Amount', 'From', 'To', 'Description'
        ])
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    for unit in st.session_state.get('partners', {}):
        if 'Invested' not in st.session_state.partners[unit].columns:
            st.session_state.partners[unit]['Invested'] = 0.0
        if 'Withdrawn' not in st.session_state.partners[unit].columns:
            st.session_state.partners[unit]['Withdrawn'] = 0.0

def redistribute_shares(partners_df, freed_share):
    """Redistribute freed shares among remaining partners"""
    if partners_df.empty or partners_df['Share'].sum() <= 0:
        return partners_df
    total_active_shares = partners_df['Share'].sum()
    partners_df['Share'] = partners_df['Share'] + (partners_df['Share'] / total_active_shares * freed_share)
    partners_df['Share'] = partners_df['Share'] * (100 / partners_df['Share'].sum())
    partners_df['Share'] = partners_df['Share'].round(2)
    return partners_df

def update_cash_balance(amount, business_unit, operation='add'):
    """Update cash balance for a business unit with validation"""
    try:
        amount = float(amount)
        if amount < 0.0:
            raise ValueError("Amount cannot be negative")
        if amount > 0.0 and amount < 0.01:
            raise ValueError("Amount must be at least 0.01")
        if business_unit not in st.session_state.cash_balance:
            st.session_state.cash_balance[business_unit] = 0.0
        if operation == 'add':
            st.session_state.cash_balance[business_unit] += amount
        else:
            if st.session_state.cash_balance[business_unit] < amount:
                raise ValueError(f"Insufficient funds in {business_unit}")
            st.session_state.cash_balance[business_unit] -= amount
    except Exception as e:
        raise ValueError(f"Error updating cash balance: {str(e)}")

def calculate_inventory_value(unit):
    """Calculate current stock quantity and value"""
    if 'inventory' not in st.session_state or st.session_state.inventory.empty:
        return 0.0, 0.0
    unit_inv = st.session_state.inventory[st.session_state.inventory['Business Unit'] == unit]
    if unit_inv.empty:
        return 0.0, 0.0
    purchases = unit_inv[unit_inv['Transaction Type'] == 'Purchase']
    sales = unit_inv[unit_inv['Transaction Type'] == 'Sale']
    current_stock = purchases['Quantity_kg'].sum() - sales['Quantity_kg'].sum()
    current_value = current_stock * st.session_state.current_price
    return round(float(current_stock), 2), round(float(current_value), 2)

def calculate_operating_expenses(unit):
    """Calculate total operating expenses"""
    if 'expenses' not in st.session_state:
        return 0.0
    expenses = st.session_state.expenses[
        (st.session_state.expenses['Business Unit'] == unit) &
        (~st.session_state.expenses['Category'].isin(['Partner Withdrawal', 'Partner Contribution']))
    ]
    return round(float(expenses['Amount'].sum()), 2)

def calculate_profit_loss(unit):
    """Calculate actual profit from sales"""
    if 'inventory' not in st.session_state:
        return 0.0, 0.0
    sales = st.session_state.inventory[
        (st.session_state.inventory['Business Unit'] == unit) &
        (st.session_state.inventory['Transaction Type'] == 'Sale')
    ]
    purchases = st.session_state.inventory[
        (st.session_state.inventory['Business Unit'] == unit) &
        (st.session_state.inventory['Transaction Type'] == 'Purchase')
    ]
    gross_profit = float(sales['Total Amount'].sum()) - float(purchases['Total Amount'].sum())
    net_profit = gross_profit - calculate_operating_expenses(unit)
    return round(gross_profit, 2), round(net_profit, 2)

def calculate_provisional_profit(unit):
    """Calculate potential profit from current inventory"""
    current_stock, inventory_value = calculate_inventory_value(unit)
    investments = float(st.session_state.investments[
        st.session_state.investments['Business Unit'] == unit
    ]['Amount'].sum()) if 'investments' in st.session_state else 0.0
    expenses = calculate_operating_expenses(unit)
    provisional = float(inventory_value) - investments - expenses
    return round(max(0.0, provisional), 2)

def calculate_partner_profits(unit):
    """Calculate profit distribution for partners with consistent withdrawal tracking"""
    if 'partners' not in st.session_state or unit not in st.session_state.partners:
        return pd.DataFrame()
    
    partners_df = st.session_state.partners[unit].copy()
    
    # Calculate base profits
    provisional = calculate_provisional_profit(unit)
    _, actual = calculate_profit_loss(unit)
    distributable = max(float(provisional), float(actual))
    
    # Calculate entitlements using the authoritative withdrawn amounts
    partners_df['Total_Entitlement'] = partners_df['Share'] / 100 * distributable
    partners_df['Available_Now'] = partners_df['Total_Entitlement'] - partners_df['Withdrawn']
    partners_df['Available_Now'] = partners_df['Available_Now'].apply(lambda x: max(0.0, float(x)))
    
    return partners_df[['Partner', 'Share', 'Total_Entitlement', 'Withdrawn', 'Available_Now']]

def calculate_combined_partner_profits():
    """Aggregate partner profits across all units"""
    combined = pd.DataFrame()
    for unit in st.session_state.cash_balance.keys():
        if unit in st.session_state.get('partners', {}):
            unit_profits = calculate_partner_profits(unit)
            if not unit_profits.empty:
                unit_profits['Business_Unit'] = unit
                combined = pd.concat([combined, unit_profits], ignore_index=True)
    if not combined.empty:
        combined = combined.groupby('Partner').agg({
            'Share': 'sum',
            'Total_Entitlement': 'sum',
            'Withdrawn': 'sum',
            'Available_Now': 'sum',
            'Business_Unit': lambda x: ', '.join(sorted(x.unique()))
        }).reset_index()
        total_shares = combined['Share'].sum()
        combined['Share_Percentage'] = (combined['Share'] / total_shares * 100).round(2)
        combined = combined[['Partner', 'Share', 'Share_Percentage', 'Total_Entitlement', 
                            'Withdrawn', 'Available_Now', 'Business_Unit']]
        numeric_cols = ['Share', 'Share_Percentage', 'Total_Entitlement', 'Withdrawn', 'Available_Now']
        combined[numeric_cols] = combined[numeric_cols].round(2)
    return combined

def record_partner_withdrawal(unit, partner, amount, description):
    """Record a partner withdrawal transaction with consistent amount tracking"""
    try:
        amount = round(float(amount), 2)
        if amount < 0.01:
            raise ValueError("Amount must be at least 0.01")
            
        # Get current available amount
        profits_df = calculate_partner_profits(unit)
        partner_data = profits_df[profits_df['Partner'] == partner]
        
        if partner_data.empty:
            raise ValueError(f"Partner {partner} not found in {unit}")
            
        available = float(partner_data['Available_Now'].iloc[0])
        
        if amount > available:
            raise ValueError(f"Insufficient funds. Max available: {available:.2f}")
        
        # Update partner's withdrawn amount FIRST
        partner_index = st.session_state.partners[unit].index[
            st.session_state.partners[unit]['Partner'] == partner
        ].tolist()[0]
        
        st.session_state.partners[unit].at[partner_index, 'Withdrawn'] += amount
        
        # Then record the expense
        new_expense = pd.DataFrame([{
            'Date': date.today(),
            'Category': 'Partner Withdrawal',
            'Amount': amount,
            'Description': description,
            'Business Unit': unit,
            'Partner': partner,
            'Payment Method': 'Bank Transfer'
        }])
        
        st.session_state.expenses = pd.concat(
            [st.session_state.expenses, new_expense],
            ignore_index=True
        )
        
        # Update cash balance
        update_cash_balance(amount, unit, 'subtract')
        
        # Record transaction
        record_transaction(
            type='Partner Withdrawal',
            amount=amount,
            from_entity=unit,
            to_entity=partner,
            description=description
        )
        
        return True
        
    except Exception as e:
        st.error(f"Withdrawal failed: {str(e)}")
        return False

def distribute_investment(unit, amount, investor, description=None):
    """Distribute investment to partners according to their shares"""
    try:
        amount = float(amount)
        if amount == 0.0:
            logging.info(f"Skipping investment distribution for {investor} as amount is 0.0")
            return
        if amount < 0.01:
            raise ValueError("Amount must be at least 0.01")
        if 'partners' not in st.session_state or unit not in st.session_state.partners:
            raise KeyError(f"Business unit {unit} not found")
        if st.session_state.partners[unit].empty:
            raise ValueError(f"No partners in {unit} to distribute to")
        
        if 'Invested' not in st.session_state.partners[unit].columns:
            st.session_state.partners[unit]['Invested'] = 0.0
            
        desc = description or f"Investment from {investor}"
        new_investment = pd.DataFrame([{
            'Date': date.today(),
            'Business Unit': unit,
            'Amount': amount,
            'Investor': investor,
            'Description': desc
        }])
        
        if 'investments' not in st.session_state:
            st.session_state.investments = pd.DataFrame(columns=[
                'Date', 'Business Unit', 'Amount', 'Investor', 'Description'
            ])
            
        duplicate_check = st.session_state.investments[
            (st.session_state.investments['Business Unit'] == unit) &
            (st.session_state.investments['Investor'] == investor) &
            (st.session_state.investments['Amount'] == amount) &
            (pd.to_datetime(st.session_state.investments['Date']) == pd.to_datetime(date.today()))
        ]
        if not duplicate_check.empty:
            raise ValueError("Duplicate investment detected")
            
        st.session_state.investments = pd.concat(
            [st.session_state.investments, new_investment],
            ignore_index=True
        )
        
        update_cash_balance(amount, unit, 'add')
        record_transaction(
            type='Investment',
            amount=amount,
            from_entity=investor,
            to_entity=unit,
            description=desc
        )
        
        total_share = float(st.session_state.partners[unit]['Share'].sum())
        for _, row in st.session_state.partners[unit].iterrows():
            share_amount = (float(row['Share']) / total_share) * amount
            # Record as investment distribution
            new_expense = pd.DataFrame([{
                'Date': date.today(),
                'Category': 'Partner Contribution',
                'Amount': share_amount,
                'Description': f"Investment distribution from {investor}",
                'Business Unit': unit,
                'Partner': row['Partner'],
                'Payment Method': 'Bank Transfer'
            }])
            st.session_state.expenses = pd.concat(
                [st.session_state.expenses, new_expense],
                ignore_index=True
            )
            # Update partner's invested amount
            partner_index = st.session_state.partners[unit].index[
                st.session_state.partners[unit]['Partner'] == row['Partner']
            ].tolist()[0]
            st.session_state.partners[unit].at[partner_index, 'Invested'] += share_amount
        return True
    except Exception as e:
        raise ValueError(f"Error distributing investment: {str(e)}")

def update_market_price(new_price):
    """Update current market price"""
    try:
        new_price = float(new_price)
        if new_price <= 0:
            raise ValueError("Price must be a positive number")
        st.session_state.current_price = new_price
        new_record = pd.DataFrame([{
            'Date': date.today(),
            'Time': datetime.now().time(),
            'Price': new_price
        }])
        if 'price_history' not in st.session_state:
            st.session_state.price_history = new_record
        else:
            st.session_state.price_history = pd.concat(
                [st.session_state.price_history, new_record],
                ignore_index=True
            )
    except Exception as e:
        raise ValueError(f"Error updating market price: {str(e)}")

def record_transaction(type, amount, from_entity, to_entity, description=None):
    """Record a financial transaction"""
    try:
        amount = float(amount)
        if amount == 0.0:
            logging.info(f"Skipping transaction recording for {type} as amount is 0.0")
            return
        if amount < 0.01:
            raise ValueError("Amount must be at least 0.01")
        new_transaction = pd.DataFrame([{
            'Date': date.today(),
            'Type': type,
            'Amount': amount,
            'From': from_entity,
            'To': to_entity,
            'Description': description or f"{type} transaction"
        }])
        if 'transactions' not in st.session_state:
            st.session_state.transactions = pd.DataFrame(columns=[
                'Date', 'Type', 'Amount', 'From', 'To', 'Description'
            ])
        st.session_state.transactions = pd.concat(
            [st.session_state.transactions, new_transaction],
            ignore_index=True
        )
    except Exception as e:
        raise ValueError(f"Error recording transaction: {str(e)}")

def get_business_unit_summary(unit):
    """Generate business unit summary"""
    try:
        cash = float(st.session_state.cash_balance.get(unit, 0.0))
        stock, stock_value = calculate_inventory_value(unit)
        gross_profit, net_profit = calculate_profit_loss(unit)
        provisional = calculate_provisional_profit(unit)
        return {
            'Cash Balance': round(cash, 2),
            'Inventory Quantity (kg)': round(float(stock), 2),
            'Inventory Value': round(float(stock_value), 2),
            'Gross Profit': round(float(gross_profit), 2),
            'Net Profit': round(float(net_profit), 2),
            'Provisional Profit': round(float(provisional), 2),
            'Operating Expenses': calculate_operating_expenses(unit),
            'Investment Total': float(st.session_state.investments[
                st.session_state.investments['Business Unit'] == unit
            ]['Amount'].sum()) if 'investments' in st.session_state else 0.0
        }
    except Exception as e:
        raise ValueError(f"Error generating business unit summary: {str(e)}")

def get_system_summary():
    """Generate system-wide summary"""
    try:
        summary = {
            'Units': {},
            'Total Cash': sum(float(v) for v in st.session_state.cash_balance.values()),
            'Total Inventory Value': sum(
                float(calculate_inventory_value(unit)[1]) for unit in st.session_state.cash_balance.keys()
            ),
            'Total Investments': float(st.session_state.investments['Amount'].sum()) 
                if 'investments' in st.session_state else 0.0,
            'Total Expenses': float(st.session_state.expenses['Amount'].sum()) 
                if 'expenses' in st.session_state else 0.0
        }
        for unit in st.session_state.cash_balance.keys():
            summary['Units'][unit] = get_business_unit_summary(unit)
        for key in ['Total Cash', 'Total Inventory Value', 'Total Investments', 'Total Expenses']:
            summary[key] = round(float(summary[key]), 2)
        return summary
    except Exception as e:
        raise ValueError(f"Error generating system summary: {str(e)}")