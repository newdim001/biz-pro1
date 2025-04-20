# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date
from utils import (
    calculate_inventory_value,
    calculate_profit_loss,
    calculate_provisional_profit,
    calculate_partner_profits,
    calculate_combined_partner_profits,
    initialize_default_data,
    update_market_price,
    get_system_summary,
    get_business_unit_summary
)
from .auth import has_permission

def show_dashboard():
    try:
        # Check user permissions
        user = st.session_state.get('user')
        if not user or not has_permission(user['role'], 'dashboard'):
            st.error("You don't have permission to access this page")
            return
        
        # Initialize default data
        initialize_default_data()
        
        st.header("Business Dashboard")
        
        # Price Management Section
        with st.expander("Daily Price Management", expanded=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                new_price = st.number_input(
                    "Update Current Market Price (AED per kg)",
                    min_value=0.0,
                    step=0.01,
                    value=float(st.session_state.current_price),
                    key="current_price_input"
                )
            
            with col2:
                st.write("")  # Add vertical spacing
                st.write("")
                if st.button("Save Price Update"):
                    try:
                        update_market_price(new_price)
                        st.success(f"Price updated to AED {new_price:,.2f} per kg")
                    except Exception as e:
                        st.error(f"Error updating market price: {str(e)}")
            
            # Display Price History
            if not st.session_state.price_history.empty:
                st.subheader("Price History (Last 30 Days)")
                history = st.session_state.price_history.copy()
                history['Date'] = pd.to_datetime(history['Date'])
                history = history.set_index('Date').last('30D').reset_index()
                
                fig = px.line(
                    history,
                    x='Date',
                    y='Price',
                    title="Market Price Trend",
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # System-wide summary metrics
        system_summary = get_system_summary()
        st.subheader("System Overview")
        
        # Calculate total stock from all units
        total_stock = sum(
            unit_data['Inventory Quantity (kg)'] 
            for unit_data in system_summary['Units'].values()
        )
        
        # Calculate total provisional profit from all units
        total_provisional = sum(
            unit_data['Provisional Profit'] 
            for unit_data in system_summary['Units'].values()
        )
        
        # Display the requested metrics in a 4-column layout
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Cash", f"AED {system_summary['Total Cash']:,.2f}")
        with col2:
            st.metric("Total Stock", f"{total_stock:,.2f} kg")
        with col3:
            st.metric("Total Inventory Value", f"AED {system_summary['Total Inventory Value']:,.2f}")
        with col4:
            st.metric("Total Provisional Profit", f"AED {total_provisional:,.2f}")
        
        # Determine which units to show based on user's role
        units_to_show = []
        if user['business_unit'] in ['All', 'Unit A']:
            units_to_show.append('Unit A')
        if user['business_unit'] in ['All', 'Unit B']:
            units_to_show.append('Unit B')
        if user['business_unit'] == 'All':
            units_to_show.append('Combined')
        
        tabs = st.tabs(units_to_show)
        
        for i, unit in enumerate(units_to_show):
            with tabs[i]:
                if unit == 'Combined':
                    show_combined_dashboard()
                else:
                    show_unit_dashboard(unit)
    
    except Exception as e:
        st.error(f"Error loading dashboard: {str(e)}")


def show_unit_dashboard(unit):
    try:
        # Get unit summary data
        unit_summary = get_business_unit_summary(unit)
        
        # Display Metrics in a more organized layout
        st.subheader(f"{unit} Performance Metrics")
        
        # First row - Core financial metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Cash Balance", f"AED {unit_summary['Cash Balance']:,.2f}")
        with col2:
            st.metric("Gross Profit", f"AED {unit_summary['Gross Profit']:,.2f}")
        with col3:
            st.metric("Net Profit", f"AED {unit_summary['Net Profit']:,.2f}")
        with col4:
            st.metric("Investments", f"AED {unit_summary['Investment Total']:,.2f}")
        
        # Second row - Inventory metrics
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("Current Stock", f"{unit_summary['Inventory Quantity (kg)']:,.2f} kg")
        with col6:
            st.metric("Inventory Value", f"AED {unit_summary['Inventory Value']:,.2f}")
        with col7:
            st.metric("Provisional Profit", f"AED {unit_summary['Provisional Profit']:,.2f}")
        with col8:
            st.metric("Operating Expenses", f"AED {unit_summary['Operating Expenses']:,.2f}")
        
        # Partner Profit Distribution
        if not st.session_state.partners[unit].empty:
            st.subheader(f"{unit} Partner Profit Distribution")
            profit_df = calculate_partner_profits(unit)
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.dataframe(
                    profit_df.style.format({
                        'Share': '{:.1f}%',
                        'Total_Entitlement': 'AED {:,.2f}',
                        'Withdrawn': 'AED {:,.2f}',
                        'Available_Now': 'AED {:,.2f}'
                    }),
                    height=400
                )
            with col2:
                fig = px.pie(
                    profit_df,
                    values='Total_Entitlement',
                    names='Partner',
                    title=f"{unit} Profit Distribution",
                    hole=0.3
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error showing {unit} dashboard: {str(e)}")


def show_combined_dashboard():
    try:
        # Get system summary data
        system_summary = get_system_summary()
        
        # Display Combined Metrics
        st.subheader("Combined Business Performance")
        
        # Calculate totals from all units
        total_stock = sum(
            unit_data['Inventory Quantity (kg)'] 
            for unit_data in system_summary['Units'].values()
        )
        total_provisional = sum(
            unit_data['Provisional Profit'] 
            for unit_data in system_summary['Units'].values()
        )
        
        # First row - Core financial metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Cash", f"AED {system_summary['Total Cash']:,.2f}")
        with col2:
            st.metric("Total Stock", f"{total_stock:,.2f} kg")
        with col3:
            st.metric("Total Inventory Value", f"AED {system_summary['Total Inventory Value']:,.2f}")
        with col4:
            st.metric("Total Provisional Profit", f"AED {total_provisional:,.2f}")
        
        # Second row - Additional metrics
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("Total Gross Profit", f"AED {sum(u['Gross Profit'] for u in system_summary['Units'].values()):,.2f}")
        with col6:
            st.metric("Total Net Profit", f"AED {sum(u['Net Profit'] for u in system_summary['Units'].values()):,.2f}")
        with col7:
            st.metric("Total Investments", f"AED {system_summary['Total Investments']:,.2f}")
        with col8:
            st.metric("Total Expenses", f"AED {sum(u['Operating Expenses'] for u in system_summary['Units'].values()):,.2f}")
        
        # Combined Partner Summary
        st.subheader("Combined Partner Summary")
        combined_partners = calculate_combined_partner_profits()
        
        if not combined_partners.empty:
            col1, col2 = st.columns([2, 1])
            with col1:
                st.dataframe(
                    combined_partners.style.format({
                        'Share': '{:.1f}%',
                        'Share_Percentage': '{:.1f}%',
                        'Total_Entitlement': 'AED {:,.2f}',
                        'Withdrawn': 'AED {:,.2f}',
                        'Available_Now': 'AED {:,.2f}'
                    }),
                    height=400
                )
            with col2:
                fig = px.pie(
                    combined_partners,
                    values='Total_Entitlement',
                    names='Partner',
                    title="Combined Profit Distribution",
                    hole=0.3
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
    
    except Exception as e:
        st.error(f"Error showing combined dashboard: {str(e)}")