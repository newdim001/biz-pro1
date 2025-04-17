import streamlit as st
import pandas as pd
import plotly.express as px
from utils import (
    calculate_inventory_value,
    calculate_profit_loss,
    calculate_provisional_profit,
    calculate_partner_profits,
    record_partner_withdrawal
)
from .auth import has_permission
def show_dashboard():
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'dashboard'):
        st.error("You don't have permission to access this page")
        return
    
    st.header("Business Overview")
    st.session_state.current_price = st.number_input(
        "Current Market Price (AED per kg)",
        min_value=0.0, step=1.0, value=st.session_state.current_price
    )
    
    # Determine which units to show based on user's business unit
    units_to_show = []
    if user['business_unit'] in ['All', 'Unit A']:
        units_to_show.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units_to_show.append('Unit B')
    
    # Add combined view if user has access to both units
    if len(units_to_show) > 1:
        units_to_show.append('Combined')
    
    unit_tabs = st.tabs(units_to_show)
    for i, unit in enumerate(units_to_show):
        with unit_tabs[i]:
            if unit == 'Combined':
                show_combined_dashboard()
            else:
                show_unit_dashboard(unit)

def show_unit_dashboard(unit):
    user = st.session_state.get('user')
    if not user or user['business_unit'] not in ['All', unit]:
        st.error(f"You don't have access to {unit}")
        return
    
    cash = st.session_state.cash_balance[unit]
    current_stock, current_value = calculate_inventory_value(unit)
    gross_profit, net_profit = calculate_profit_loss(unit)
    unit_investment = st.session_state.investments[
        st.session_state.investments['Business Unit'] == unit
    ]['Amount'].sum() if 'investments' in st.session_state else 0
    
    cols = st.columns(3)
    with cols[0]:
        st.metric(f"{unit} Cash Balance", f"AED {cash:,.2f}")
        st.metric("Inventory Value", f"AED {current_value:,.2f}")
    with cols[1]:
        st.metric("Current Stock", f"{current_stock:.2f} kg")
        st.metric("Investments", f"AED {unit_investment:,.2f}")
    with cols[2]:
        st.metric("Gross Profit", f"AED {gross_profit:,.2f}")
        st.metric("Net Profit", f"AED {net_profit:,.2f}")

    provisional_profit = calculate_provisional_profit(unit)
    st.markdown(f"""
        <div class="stMetric provisional-profit">
            <div>Provisional Profit</div>
            <div>AED {provisional_profit:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

    if not st.session_state.partners[unit].empty:
        st.subheader(f"{unit} Partner Profit Distribution")
        profit_df = calculate_partner_profits(unit)
        
        with st.expander("Partner Withdrawal"):
            with st.form(f"partner_withdrawal_{unit}"):
                partner = st.selectbox(
                    "Partner",
                    profit_df['Partner'].unique(),
                    key=f"withdraw_partner_{unit}"
                )
                available = profit_df[profit_df['Partner'] == partner]['Provisional_Share'].values[0]
                amount = st.number_input(
                    "Amount (AED)",
                    min_value=0.0,
                    max_value=available,
                    step=100.0,
                    key=f"withdraw_amount_{unit}",
                    help=f"Available: AED {available:,.2f}"
                )
                description = st.text_input(
                    "Description",
                    key=f"withdraw_desc_{unit}"
                )
                if st.form_submit_button("Record Withdrawal"):
                    record_partner_withdrawal(unit, partner, amount, description)
                    st.success(f"Withdrawal of AED {amount:,.2f} recorded for {partner}")
        
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
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

def show_combined_dashboard():
    user = st.session_state.get('user')
    if not user or user['business_unit'] != 'All':
        st.error("You don't have access to the combined view")
        return
    
    cash = sum(st.session_state.cash_balance.values())
    stock_a, value_a = calculate_inventory_value('Unit A')
    stock_b, value_b = calculate_inventory_value('Unit B')
    total_stock = stock_a + stock_b
    total_value = value_a + value_b
    gross_a, net_a = calculate_profit_loss('Unit A')
    gross_b, net_b = calculate_profit_loss('Unit B')
    total_net = net_a + net_b
    combined_investment = st.session_state.investments['Amount'].sum() if 'investments' in st.session_state else 0
    
    cols = st.columns(3)
    with cols[0]:
        st.metric("Total Cash", f"AED {cash:,.2f}")
        st.metric("Inventory Value", f"AED {total_value:,.2f}")
    with cols[1]:
        st.metric("Current Stock", f"{total_stock:.2f} kg")
        st.metric("Investments", f"AED {combined_investment:,.2f}")
    with cols[2]:
        st.metric("Gross Profit", f"AED {gross_a + gross_b:,.2f}")
        st.metric("Net Profit", f"AED {total_net:,.2f}")

    provisional_profit = calculate_provisional_profit('Unit A') + calculate_provisional_profit('Unit B')
    st.markdown(f"""
        <div class="stMetric provisional-profit">
            <div>Provisional Profit</div>
            <div>AED {provisional_profit:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

    st.subheader("Combined Partner Profit Distribution")
    combined_profit_df = pd.concat([
        calculate_partner_profits('Unit A').assign(Unit='Unit A'),
        calculate_partner_profits('Unit B').assign(Unit='Unit B')
    ], ignore_index=True)
    
    if not combined_profit_df.empty:
        cols = st.columns([2, 1])
        with cols[0]:
            st.dataframe(
                combined_profit_df.style.format({
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
                combined_profit_df, 
                values='Provisional_Share', 
                names='Partner',
                title="Remaining Provisional Profit"
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No partners added yet")