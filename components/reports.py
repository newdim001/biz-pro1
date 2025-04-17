import streamlit as st
import pandas as pd
import plotly.express as px
from utils import (
    calculate_inventory_value,
    calculate_profit_loss,
    calculate_partner_profits,
    calculate_combined_partner_profits
)
from .auth import has_permission

def show_reports():
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'reports'):
        st.error("You don't have permission to access this page")
        return
    
    st.header("Business Reports")
    
    # Determine which units to show based on user's business unit
    units_to_show = []
    if user['business_unit'] in ['All', 'Unit A']:
        units_to_show.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units_to_show.append('Unit B')
    if len(units_to_show) > 1:
        units_to_show.append('Combined')
    
    report_type = st.selectbox("Report Type", [
        "Financial Summary",
        "Inventory Report",
        "Partner Report"
    ])
    
    if report_type == "Financial Summary":
        show_financial_summary(units_to_show)
    elif report_type == "Inventory Report":
        show_inventory_report(units_to_show)
    elif report_type == "Partner Report":
        show_partner_report(units_to_show)

def show_financial_summary(units_to_show):
    st.subheader("Financial Summary")
    
    data = []
    for unit in units_to_show:
        if unit == 'Combined':
            cash = sum(st.session_state.cash_balance.values())
            stock_a, value_a = calculate_inventory_value('Unit A')
            stock_b, value_b = calculate_inventory_value('Unit B')
            total_stock = stock_a + stock_b
            total_value = value_a + value_b
            gross_a, net_a = calculate_profit_loss('Unit A')
            gross_b, net_b = calculate_profit_loss('Unit B')
            total_net = net_a + net_b
            combined_investment = st.session_state.investments['Amount'].sum() if 'investments' in st.session_state else 0
            
            data.append({
                'Unit': 'Combined',
                'Cash Balance': cash,
                'Inventory Value': total_value,
                'Current Stock': total_stock,
                'Investments': combined_investment,
                'Gross Profit': gross_a + gross_b,
                'Net Profit': total_net
            })
        else:
            cash = st.session_state.cash_balance[unit]
            current_stock, current_value = calculate_inventory_value(unit)
            gross_profit, net_profit = calculate_profit_loss(unit)
            unit_investment = st.session_state.investments[
                st.session_state.investments['Business Unit'] == unit
            ]['Amount'].sum() if 'investments' in st.session_state else 0
            
            data.append({
                'Unit': unit,
                'Cash Balance': cash,
                'Inventory Value': current_value,
                'Current Stock': current_stock,
                'Investments': unit_investment,
                'Gross Profit': gross_profit,
                'Net Profit': net_profit
            })
    
    df = pd.DataFrame(data)
    st.dataframe(df.style.format({
        'Cash Balance': 'AED {:,.2f}',
        'Inventory Value': 'AED {:,.2f}',
        'Investments': 'AED {:,.2f}',
        'Gross Profit': 'AED {:,.2f}',
        'Net Profit': 'AED {:,.2f}'
    }))

def show_inventory_report(units_to_show):
    st.subheader("Inventory Report")
    
    for unit in units_to_show:
        if unit == 'Combined':
            st.write("### Combined Inventory")
            inventory = st.session_state.inventory.copy()
        else:
            st.write(f"### {unit} Inventory")
            inventory = st.session_state.inventory[
                st.session_state.inventory['Business Unit'] == unit
            ].copy()
        
        if not inventory.empty:
            inventory['Date'] = pd.to_datetime(inventory['Date'])
            inventory['Month'] = inventory['Date'].dt.to_period('M')
            
            # Monthly summary
            monthly_summary = inventory.groupby(['Month', 'Transaction Type']).agg({
                'Quantity_kg': 'sum',
                'Total Amount': 'sum'
            }).unstack().fillna(0)
            
            st.write("#### Monthly Summary")
            st.dataframe(monthly_summary.style.format({
                ('Quantity_kg', 'Purchase'): '{:.2f} kg',
                ('Quantity_kg', 'Sale'): '{:.2f} kg',
                ('Total Amount', 'Purchase'): 'AED {:,.2f}',
                ('Total Amount', 'Sale'): 'AED {:,.2f}'
            }))
            
            # Transaction details
            st.write("#### Transaction Details")
            st.dataframe(inventory.sort_values('Date', ascending=False))
        else:
            st.info(f"No inventory data available for {unit}")

def show_partner_report(units_to_show):
    st.subheader("Partner Report")
    
    for unit in units_to_show:
        if unit == 'Combined':
            st.write("### Combined Partner Summary")
            profit_df = calculate_combined_partner_profits()
        else:
            st.write(f"### {unit} Partner Summary")
            profit_df = calculate_partner_profits(unit)
        
        if not profit_df.empty:
            cols = st.columns([2, 1])
            with cols[0]:
                st.dataframe(
                    profit_df.style.format({
                        'Share': '{:.1f}%',
                        'Profit_Share': 'AED {:,.2f}',
                        'Provisional_Share': 'AED {:,.2f}',
                        'Amount': 'AED {:,.2f}',
                        'Net_Amount': 'AED {:,.2f}'
                    }),
                    height=400
                )
            with cols[1]:
                fig = px.pie(
                    profit_df, 
                    values='Provisional_Share', 
                    names='Partner',
                    title="Remaining Provisional Profit"
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No partners added for {unit} yet")