import streamlit as st
import pandas as pd
from utils import redistribute_shares
from .auth import has_permission

def initialize_partnership_data():
    """Initialize partnership data in session state if not exists"""
    if 'partners' not in st.session_state:
        st.session_state.partners = {
            'Unit A': pd.DataFrame(columns=['Partner', 'Share', 'Withdrawn']),
            'Unit B': pd.DataFrame(columns=['Partner', 'Share', 'Withdrawn'])
        }

def show_partnership():
    user = st.session_state.get('user')
    if not user or not has_permission(user['role'], 'partnership'):
        st.error("You don't have permission to access this page")
        return
    
    initialize_partnership_data()
    
    st.header("Partnership Management")
    
    # Determine which units to show based on user's business unit
    units_to_show = []
    if user['business_unit'] in ['All', 'Unit A']:
        units_to_show.append('Unit A')
    if user['business_unit'] in ['All', 'Unit B']:
        units_to_show.append('Unit B')
    
    unit_tabs = st.tabs(units_to_show)
    
    for i, unit in enumerate(units_to_show):
        with unit_tabs[i]:
            st.subheader(f"{unit} Ownership Structure")
            cols = st.columns(2)
            
            with cols[0]:
                show_existing_partners(unit)
            with cols[1]:
                show_add_partner_form(unit)

def show_existing_partners(unit):
    partners_df = st.session_state.partners[unit]
    
    if not partners_df.empty:
        st.write("Current Partners:")
        total_allocated = partners_df['Share'].sum()
        st.dataframe(partners_df)
        st.metric("Total Allocated", f"{total_allocated:.2f}%")
        remaining_pct = max(0, 100 - total_allocated)
        st.metric("Remaining", f"{remaining_pct:.2f}%")
        
        if st.checkbox(f"Remove Partner from {unit}", key=f"remove_checkbox_{unit}"):
            partner_to_remove = st.selectbox(
                "Select Partner to Remove",
                partners_df['Partner'].unique(),
                key=f"remove_{unit}"
            )
            if st.button(f"Confirm Removal of {partner_to_remove}", key=f"confirm_remove_{unit}"):
                removed_share = partners_df.loc[partners_df['Partner'] == partner_to_remove, 'Share'].values[0]
                st.session_state.partners[unit] = partners_df[partners_df['Partner'] != partner_to_remove]
                st.session_state[f'removed_share_{unit}'] = removed_share
                st.session_state[f'partner_removed_{unit}'] = True
                st.success(f"{partner_to_remove} removed. Freed share: {removed_share:.1f}%")
        
        if st.session_state.get(f'partner_removed_{unit}', False):
            handle_freed_share(unit)
    else:
        st.info(f"No partners added for {unit} yet")

def handle_freed_share(unit):
    removed_share = st.session_state.get(f'removed_share_{unit}', 0)
    st.subheader(f"Handle Freed Share ({removed_share:.1f}%)")
    action = st.radio(
        "Action",
        ["Redistribute Among Existing Partners", "Assign to a New Partner"],
        key=f"action_{unit}"
    )
    
    if action == "Redistribute Among Existing Partners":
        if st.button(f"Redistribute {removed_share:.1f}%", key=f"redist_{unit}"):
            if not st.session_state.partners[unit].empty:
                st.session_state.partners[unit] = redistribute_shares(
                    st.session_state.partners[unit],
                    removed_share
                )
                st.success(f"Redistributed {removed_share:.1f}% among existing partners")
                del st.session_state[f'removed_share_{unit}']
                del st.session_state[f'partner_removed_{unit}']
            else:
                st.warning("No existing partners to redistribute to")
    elif action == "Assign to a New Partner":
        with st.form(f"new_partner_form_{unit}"):
            new_partner_name = st.text_input("New Partner Name", key=f"new_name_{unit}")
            new_partner_share = st.number_input(
                "Share Percentage",
                min_value=0.1,
                max_value=float(removed_share),
                value=float(min(20, removed_share)),
                step=0.1,
                format="%.1f",
                key=f"new_share_{unit}"
            )
            if st.form_submit_button(f"Add New Partner to {unit}"):
                if new_partner_name.strip() == "":
                    st.error("Please enter a valid partner name")
                elif new_partner_name in st.session_state.partners[unit]['Partner'].values:
                    st.error("Partner with this name already exists")
                else:
                    st.session_state.partners[unit] = pd.concat([
                        st.session_state.partners[unit],
                        pd.DataFrame([{'Partner': new_partner_name, 'Share': new_partner_share, 'Withdrawn': 0}])
                    ], ignore_index=True)
                    remaining_share = removed_share - new_partner_share
                    if remaining_share > 0 and not st.session_state.partners[unit].empty:
                        st.session_state.partners[unit] = redistribute_shares(
                            st.session_state.partners[unit],
                            remaining_share
                        )
                    st.success(f"Added {new_partner_name} with {new_partner_share:.1f}% share")
                    del st.session_state[f'removed_share_{unit}']
                    del st.session_state[f'partner_removed_{unit}']

def show_add_partner_form(unit):
    st.subheader(f"Add New Partner - {unit}")
    with st.form(f"add_partner_form_{unit}"):
        partner_name = st.text_input("Partner Name", key=f"name_{unit}")
        
        partners_df = st.session_state.partners[unit]
        if not partners_df.empty:
            total_allocated = partners_df['Share'].sum()
            remaining_pct = max(0, 100 - total_allocated)
            if remaining_pct > 0:
                share = st.slider(
                    "Share Percentage",
                    min_value=0.1,
                    max_value=float(remaining_pct),
                    value=float(min(20, remaining_pct)),
                    step=0.1,
                    format="%.1f%%",
                    key=f"share_{unit}"
                )
            else:
                st.warning("No remaining share available")
                share = 0
        else:
            share = st.slider(
                "Share Percentage",
                min_value=0.1,
                max_value=100.0,
                value=40.0,
                step=0.1,
                format="%.1f%%",
                key=f"share_{unit}"
            )
        
        if st.form_submit_button(f"Add Partner to {unit}"):
            if partner_name.strip() == "":
                st.error("Please enter a partner name")
            elif share <= 0:
                st.error("Share percentage must be greater than 0")
            elif partner_name in partners_df['Partner'].values:
                st.error("Partner with this name already exists")
            else:
                current_total = partners_df['Share'].sum()
                if (current_total + share) > 100:
                    st.error(f"Adding {share:.1f}% would exceed 100% (current total: {current_total:.1f}%)")
                else:
                    st.session_state.partners[unit] = pd.concat([
                        partners_df,
                        pd.DataFrame([{'Partner': partner_name, 'Share': share, 'Withdrawn': 0}])
                    ], ignore_index=True)
                    st.success(f"Added {partner_name} with {share:.1f}% share to {unit}")