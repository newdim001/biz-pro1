import streamlit as st
import pandas as pd
import plotly.express as px
from utils import (
    calculate_inventory_value,
    calculate_profit_loss,
    calculate_partner_profits,
    calculate_combined_partner_profits,
    initialize_default_data
)
from .auth import has_permission

def show_reports():
    """Business reporting dashboard"""
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'reports'):
        st.error("Permission denied")
        return
    
    initialize_default_data()
    
    st.header("📈 Business Reports")
    
    # Available units
    units = []
    if user['business_unit'] in ['All', 'Unit A']:
        units.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units.append('Unit B')
    if user['business_unit'] == 'All':
        units.append('Combined')
    
    # Report selection
    report_type = st.selectbox(
        "Select Report Type",
        ["Financial Summary", "Inventory Analysis", "Partner Distributions"]
    )
    
    if report_type == "Financial Summary":
        show_financial_report(units)
    elif report_type == "Inventory Analysis":
        show_inventory_report(units)
    else:
        show_partner_report(units)

def show_financial_report(units):
    """Financial performance report"""
    st.subheader("💰 Financial Summary")
    
    data = []
    for unit in units:
        if unit == 'Combined':
            cash = sum(st.session_state.cash_balance.values())
            stock_a, val_a = calculate_inventory_value('Unit A')
            stock_b, val_b = calculate_inventory_value('Unit B')
            gross_a, net_a = calculate_profit_loss('Unit A')
            gross_b, net_b = calculate_profit_loss('Unit B')
            
            data.append({
                'Unit': 'Combined',
                'Cash': cash,
                'Inventory Value': val_a + val_b,
                'Gross Profit': gross_a + gross_b,
                'Net Profit': net_a + net_b
            })
        else:
            cash = st.session_state.cash_balance.get(unit, 0)
            stock, val = calculate_inventory_value(unit)
            gross, net = calculate_profit_loss(unit)
            
            data.append({
                'Unit': unit,
                'Cash': cash,
                'Inventory Value': val,
                'Gross Profit': gross,
                'Net Profit': net
            })
    
    df = pd.DataFrame(data)
    
    # Display
    st.dataframe(
        df.style.format({
            'Cash': 'AED {:,.2f}',
            'Inventory Value': 'AED {:,.2f}',
            'Gross Profit': 'AED {:,.2f}',
            'Net Profit': 'AED {:,.2f}'
        }),
        height=200
    )
    
    # Visualizations
    fig = px.bar(
        df.melt(id_vars=['Unit'], value_vars=['Gross Profit', 'Net Profit']),
        x='Unit', y='value', color='variable',
        title="Profit Comparison",
        labels={'value': 'Amount (AED)'}
    )
    st.plotly_chart(fig, use_container_width=True)

def show_inventory_report(units):
    """Inventory analysis report"""
    st.subheader("📦 Inventory Analysis")
    
    for unit in units:
        if unit == 'Combined':
            inventory = st.session_state.inventory.copy()
            st.write("### Combined Inventory")
        else:
            inventory = st.session_state.inventory[
                st.session_state.inventory['Business Unit'] == unit
            ].copy()
            st.write(f"### {unit} Inventory")
        
        if not inventory.empty:
            # Current status
            stock, value = calculate_inventory_value(unit.split()[-1])
            cols = st.columns(2)
            cols[0].metric("Current Stock", f"{stock:,.2f} kg")
            cols[1].metric("Current Value", f"AED {value:,.2f}")
            
            # Transactions
            st.dataframe(
                inventory.sort_values('Date', ascending=False).style.format({
                    'Quantity_kg': '{:,.2f} kg',
                    'Unit Price': 'AED {:,.2f}',
                    'Total Amount': 'AED {:,.2f}'
                }),
                height=300
            )
        else:
            st.info("No inventory data")

def show_partner_report(units):
    """Partner distributions report"""
    st.subheader("👥 Partner Distributions")
    
    for unit in units:
        if unit == 'Combined':
            st.write("### Combined Partners")
            data = calculate_combined_partner_profits()
        else:
            st.write(f"### {unit} Partners")
            data = calculate_partner_profits(unit)
        
        if not data.empty:
            # Metrics
            total = data['Provisional_Share'].sum()
            withdrawn = data['Amount'].sum()
            
            cols = st.columns(3)
            cols[0].metric("Total Available", f"AED {total:,.2f}")
            cols[1].metric("Total Withdrawn", f"AED {withdrawn:,.2f}")
            cols[2].metric("Net Payable", f"AED {total - withdrawn:,.2f}")
            
            # Detailed view
            st.dataframe(
                data.style.format({
                    'Share': '{:.1f}%',
                    'Profit_Share': 'AED {:,.2f}',
                    'Provisional_Share': 'AED {:,.2f}',
                    'Amount': 'AED {:,.2f}'
                })
            )
            
            # Visualization
            fig = px.pie(
                data, values='Provisional_Share', names='Partner',
                title="Available Profit Distribution"
            )
            st.plotly_chart(fig)
        else:
            st.info("No partner data")