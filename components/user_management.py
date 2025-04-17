import streamlit as st
import pandas as pd
from .auth import (
    get_users, create_user, delete_user, update_user,
    ROLES
)

def show_user_management():
    st.header("User Management")
    
    # Create new user form
    with st.expander("Add New User", expanded=True):
        with st.form("add_user_form", clear_on_submit=True):
            cols = st.columns(2)
            with cols[0]:
                username = st.text_input("Username")
                full_name = st.text_input("Full Name")
            with cols[1]:
                role = st.selectbox("Role", list(ROLES.keys()), 
                                  format_func=lambda x: x.capitalize())
                business_unit = st.selectbox("Business Unit", 
                                           ["All", "Unit A", "Unit B"])
            
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Create User"):
                try:
                    if password != confirm_password:
                        st.error("Passwords do not match")
                    elif not username or not password:
                        st.error("Username and password are required")
                    else:
                        if create_user(username, password, full_name, role, business_unit):
                            st.success(f"User {username} created successfully")
                        else:
                            st.error("Username already exists")
                except Exception as e:
                    st.error(f"Error creating user: {str(e)}")

    # User list with edit/delete options
    st.subheader("Current Users")
    try:
        users = get_users()
        if users:
            display_user_table(users)
        else:
            st.info("No users found")
    except Exception as e:
        st.error(f"Error loading users: {str(e)}")

def display_user_table(users):
    df = pd.DataFrame(users)
    df = df[['username', 'full_name', 'role', 'business_unit', 'created_at', 'last_login']]
    st.dataframe(df)
    
    with st.expander("Manage Users"):
        user_to_edit = st.selectbox(
            "Select User to Edit",
            [u['username'] for u in users],
            key="edit_user_select"
        )
        
        user_data = next(u for u in users if u['username'] == user_to_edit)
        show_user_edit_form(user_data)
        show_delete_button(user_data)

def show_user_edit_form(user_data):
    with st.form(f"edit_user_{user_data['id']}"):
        cols = st.columns(2)
        with cols[0]:
            new_full_name = st.text_input("Full Name", value=user_data['full_name'])
            new_role = st.selectbox(
                "Role",
                list(ROLES.keys()),
                index=list(ROLES.keys()).index(user_data['role']),
                format_func=lambda x: x.capitalize()
            )
        with cols[1]:
            new_business_unit = st.selectbox(
                "Business Unit",
                ["All", "Unit A", "Unit B"],
                index=["All", "Unit A", "Unit B"].index(user_data['business_unit'])
            )
            new_password = st.text_input("New Password (leave blank to keep current)", 
                                       type="password")
        
        if st.form_submit_button("Update User"):
            try:
                update_user(
                    user_data['id'],
                    full_name=new_full_name,
                    role=new_role,
                    business_unit=new_business_unit,
                    password=new_password if new_password else None
                )
                st.success("User updated successfully")
            except Exception as e:
                st.error(f"Error updating user: {str(e)}")

def show_delete_button(user_data):
    if st.button("Delete User", key=f"delete_{user_data['id']}"):
        with st.expander("Confirm Deletion", expanded=True):
            st.warning(f"Are you sure you want to delete user {user_data['username']}?")
            if st.button(f"Confirm Delete {user_data['username']}", 
                        key=f"confirm_delete_{user_data['id']}",
                        type="primary"):
                try:
                    delete_user(user_data['id'])
                    st.success("User deleted successfully")
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error deleting user: {str(e)}")
            if st.button("Cancel", key=f"cancel_delete_{user_data['id']}"):
                st.experimental_rerun()