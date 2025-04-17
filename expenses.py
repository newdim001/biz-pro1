import streamlit as st
import pandas as pd
from datetime import date
from utils import update_cash_balance, calculate_partner_profits, record_partner_withdrawal
from .auth import has_permission

def show_expenses():
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'expenses'):
        st.error("You don't have permission to access this page")
        return
    
    st.header("Expense Tracking")
    
    # Determine which units to show based on user's business unit
    units_to_show = []
    if user['business_unit'] in ['All', 'Unit A']:
        units_to_show.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units_to_show.append('Unit B')
    
    unit_tabs = st.tabs(units_to_show)
    
    for i, unit in enumerate(units_to_show):
        with unit_tabs[i]:
            tab1, tab2 = st.tabs(["Regular Expenses", "Profit Withdrawals"])
            
            with tab1:
                with st.form(f"expense_form_{unit}", clear_on_submit=True):
                    st.subheader(f"Record Expense - {unit}")
                    cols = st.columns(2)
                    with cols[0]:
                        exp_date = st.date_input("Date", value=date.today())
                        amount = st.number_input("Amount (AED)", min_value=0.0, step=0.01)
                    with cols[1]:
                        category = st.selectbox("Category", [
                            "Staff Salaries", "Utilities", "Rent", 
                            "Administration", "Other"
                        ])
                        description = st.text_input("Description")
                    
                    if st.form_submit_button(f"Record Expense for {unit}"):
                        new_expense = pd.DataFrame([{
                            'Date': exp_date,
                            'Category': category,
                            'Amount': amount,
                            'Description': description,
                            'Business Unit': unit,
                            'Partner': None
                        }])
                        st.session_state.expenses = pd.concat([st.session_state.expenses, new_expense], ignore_index=True)
                        update_cash_balance(amount, unit, 'subtract')
                        st.success(f"Expense recorded for {unit}!")
            
            with tab2:
                if not st.session_state.partners[unit].empty:
                    st.subheader(f"Profit Withdrawals - {unit}")
                    profit_df = calculate_partner_profits(unit)
                    
                    with st.form(f"profit_withdrawal_form_{unit}", clear_on_submit=True):
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
                            help=f"Available: AED {available:,.2f}" if available > 0 else "No profits available"
                        )
                        
                        description = st.text_input(
                            "Purpose",
                            key=f"withdraw_desc_{unit}"
                        )
                        
                        if st.form_submit_button("Record Withdrawal"):
                            if available <= 0:
                                st.error("No available profits for withdrawal")
                            elif amount > available:
                                st.error(f"Cannot withdraw more than AED {available:,.2f}")
                            else:
                                record_partner_withdrawal(
                                    unit=unit,
                                    partner=partner,
                                    amount=amount,
                                    description=description
                                )
                                st.success(f"Withdrawal of AED {amount:,.2f} recorded for {partner}")
                    
                    st.subheader("Partner Profit Summary")
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
                else:
                    st.info(f"No partners added for {unit} yet")