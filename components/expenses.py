import streamlit as st
import pandas as pd
from datetime import date
from utils import (
    update_cash_balance,
    calculate_partner_profits,
    record_partner_withdrawal,
    initialize_default_data,
    record_transaction
)
from .auth import has_permission

def show_expenses():
    """Display and manage business expenses and partner withdrawals"""
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'expenses'):
        st.error("Permission denied")
        return
    
    initialize_default_data()
    
    st.header("💰 Expense Management")
    
    units_to_show = []
    if user['business_unit'] in ['All', 'Unit A']:
        units_to_show.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units_to_show.append('Unit B')
    
    tabs = st.tabs(units_to_show)
    
    for i, unit in enumerate(units_to_show):
        with tabs[i]:
            tab1, tab2 = st.tabs(["Business Expenses", "Partner Withdrawals"])
            
            with tab1:
                with st.form(f"expense_form_{unit}", clear_on_submit=True):
                    st.subheader(f"New Expense - {unit}")
                    
                    cols = st.columns(2)
                    with cols[0]:
                        exp_date = st.date_input("Date*", value=date.today())
                        amount = st.number_input(
                            "Amount (AED)*", 
                            min_value=0.01,
                            step=0.01,
                            value=100.00,
                            format="%.2f"
                        )
                    with cols[1]:
                        category = st.selectbox("Category*", [
                            "Operational", "Personnel", "Logistics", "Marketing", 
                            "Utilities", "Rent", "Other"
                        ])
                        payment_method = st.selectbox("Payment Method*", [
                            "Cash", "Bank Transfer", "Credit Card", "Cheque"
                        ])
                    
                    description = st.text_input("Description*", placeholder="Purpose of expense")
                    
                    submitted = st.form_submit_button("Record Expense")
                    
                    if submitted:
                        try:
                            if not description:
                                st.error("Description is required")
                                return
                            
                            amount = float(amount)
                            if amount < 0.01:
                                st.error("Amount must be at least 0.01 AED")
                                return
                            
                            new_expense = pd.DataFrame([{
                                'Date': exp_date,
                                'Category': category,
                                'Amount': amount,
                                'Description': description,
                                'Business Unit': unit,
                                'Partner': None,
                                'Payment Method': payment_method
                            }])
                            
                            st.session_state.expenses = pd.concat(
                                [st.session_state.expenses, new_expense],
                                ignore_index=True
                            )
                            
                            update_cash_balance(amount, unit, 'subtract')
                            record_transaction(
                                type='Expense',
                                amount=amount,
                                from_entity=unit,
                                to_entity=category,
                                description=description
                            )
                            
                            st.success("Expense recorded successfully!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error recording expense: {str(e)}")
                
                if not st.session_state.expenses.empty:
                    unit_expenses = st.session_state.expenses[
                        (st.session_state.expenses['Business Unit'] == unit) &
                        (st.session_state.expenses['Partner'].isna())
                    ]
                    
                    if not unit_expenses.empty:
                        st.subheader("Recent Expenses")
                        st.dataframe(
                            unit_expenses.sort_values('Date', ascending=False).head(10),
                            hide_index=True,
                            use_container_width=True
                        )
            
            with tab2:
                st.subheader(f"Partner Withdrawals - {unit}")
                profit_df = calculate_partner_profits(unit)
                
                if not profit_df.empty:
                    form = st.form(key=f"withdrawal_form_{unit}")
                    
                    with form:
                        partner = st.selectbox(
                            "Partner*",
                            profit_df['Partner'].unique()
                        )
                        
                        available = float(profit_df.loc[
                            profit_df['Partner'] == partner, 
                            'Available_Now'
                        ].values[0])
                        
                        cols = st.columns(2)
                        with cols[0]:
                            amount = st.number_input(
                                "Amount (AED)*",
                                min_value=0.01,
                                max_value=available,
                                value=min(1000.00, available),
                                step=100.00,
                                format="%.2f"
                            )
                        with cols[1]:
                            payment_method = st.selectbox(
                                "Payment Method*",
                                ["Bank Transfer", "Cash", "Cheque"]
                            )
                        
                        description = st.text_input(
                            "Purpose*",
                            placeholder="Reason for withdrawal"
                        )
                        
                        submitted = form.form_submit_button("Process Withdrawal")
                        
                        if submitted:
                            try:
                                if not description:
                                    st.error("Purpose is required")
                                    return
                                
                                amount = float(amount)
                                if amount < 0.01:
                                    st.error("Amount must be at least 0.01 AED")
                                    return
                                
                                if amount > available:
                                    st.error(f"Amount cannot exceed available balance of {available:.2f} AED")
                                    return
                                
                                record_partner_withdrawal(
                                    unit=unit,
                                    partner=partner,
                                    amount=amount,
                                    description=f"{description} ({payment_method})"
                                )
                                st.success("Withdrawal processed successfully!")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"Error processing withdrawal: {str(e)}")
                    
                    st.subheader("Partner Profit Distribution")
                    st.dataframe(
                        profit_df,
                        column_config={
                            "Partner": "Partner",
                            "Share": st.column_config.NumberColumn("Share %", format="%.1f"),
                            "Total_Entitlement": st.column_config.NumberColumn("Total", format="AED %.2f"),
                            "Withdrawn": st.column_config.NumberColumn("Withdrawn", format="AED %.2f"),
                            "Available_Now": st.column_config.NumberColumn("Available", format="AED %.2f")
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("No partners available for this business unit")

if __name__ == "__main__":
    show_expenses()