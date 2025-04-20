import streamlit as st
import pandas as pd
from datetime import date
from utils import (
    distribute_investment,
    initialize_default_data
)
from .auth import has_permission

def show_investments():
    """Complete investment management interface"""
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'investments'):
        st.error("Permission denied")
        return
    
    initialize_default_data()
    
    st.header("💼 Investment Management")
    
    units = []
    if user['business_unit'] in ['All', 'Unit A']:
        units.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units.append('Unit B')
    
    tabs = st.tabs(units)
    
    for i, unit in enumerate(units):
        with tabs[i]:
            with st.form(f"invest_form_{unit}", clear_on_submit=True):
                st.subheader(f"New Investment - {unit}")
                
                cols = st.columns(2)
                with cols[0]:
                    inv_date = st.date_input("Date*", date.today())
                    amount = st.number_input(
                        "Amount (AED)*", 
                        min_value=1.0,
                        step=100.0,
                        value=1000.0,
                        format="%.2f"
                    )
                with cols[1]:
                    investor = st.text_input("Investor*", placeholder="Name/Company")
                    desc = st.text_input("Description", placeholder="Purpose")
                
                if st.form_submit_button("Record Investment"):
                    if not investor:
                        st.error("Investor name required")
                    else:
                        success = distribute_investment(
                            unit=unit,
                            amount=amount,
                            investor=investor,
                            description=desc or f"Investment from {investor}"
                        )
                        if success:
                            st.success(f"✅ AED {amount:,.2f} invested in {unit}")
                            st.rerun()
                        else:
                            st.error("Failed to record investment")
            
            st.subheader(f"📋 {unit} Investment History")
            if 'investments' in st.session_state:
                unit_inv = st.session_state.investments[
                    st.session_state.investments['Business Unit'] == unit
                ]
                
                if not unit_inv.empty:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.dataframe(
                            unit_inv.sort_values('Date', ascending=False).style.format({
                                'Amount': 'AED {:,.2f}',
                                'Date': lambda x: x.strftime('%Y-%m-%d')
                            }),
                            height=300,
                            use_container_width=True
                        )
                    with col2:
                        total = unit_inv['Amount'].sum()
                        last = unit_inv.iloc[-1]
                        st.metric("Total Invested", f"AED {total:,.2f}")
                        st.metric("Last Investment", 
                                 f"AED {last['Amount']:,.2f}", 
                                 last['Investor'])
                    
                    csv = unit_inv.to_csv(index=False)
                    st.download_button(
                        "📥 Export CSV",
                        data=csv,
                        file_name=f"{unit}_investments.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No investments recorded")
            else:
                st.info("No investments recorded")

if __name__ == "__main__":
    show_investments()