import streamlit as st
from data.session_state import initialize_session_state
from components.styles import get_common_styles
from components.dashboard import show_dashboard
from components.inventory import show_inventory
from components.investments import show_investments
from components.expenses import show_expenses
from components.partnership import show_partnership
from components.reports import show_reports
from components.user_management import show_user_management
from components.auth import (
    authenticate, create_session, validate_session, logout,
    has_permission
)

def show_login():
    st.markdown(get_common_styles(), unsafe_allow_html=True)
    st.markdown('<p class="main-title">BizMaster Pro - Login</p>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            try:
                user = authenticate(username, password)
                if user:
                    session_id = create_session(user['id'])
                    st.session_state['session_id'] = session_id
                    st.session_state['user'] = user
                    st.success("Login successful! Please refresh the page.")
                    st.stop()
                else:
                    st.error("Invalid username or password")
            except Exception as e:
                st.error(f"Login error: {str(e)}")

def main():
    initialize_session_state()
    st.markdown(get_common_styles(), unsafe_allow_html=True)
    
    if 'session_id' in st.session_state:
        try:
            user = validate_session(st.session_state['session_id'])
            if not user:
                del st.session_state['session_id']
                if 'user' in st.session_state:
                    del st.session_state['user']
                st.rerun()
            else:
                st.session_state['user'] = user
        except Exception as e:
            st.error(f"Session validation error: {str(e)}")

    if 'user' not in st.session_state:
        show_login()
        return

    user = st.session_state['user']
    st.markdown(f'<p class="main-title">BizMaster Pro - Welcome {user["full_name"]} ({user["role"].capitalize()})</p>', 
                unsafe_allow_html=True)

    initialize_session_state()

    with st.sidebar:
        st.markdown(f'<p style="font-size:12px;"><strong>Logged in as:</strong> {user["full_name"]}</p>', 
                    unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:12px;"><strong>Role:</strong> {user["role"].capitalize()}</p>', 
                    unsafe_allow_html=True)
        st.markdown(f'<p style="font-size:12px;"><strong>Business Unit:</strong> {user["business_unit"]}</p>', 
                    unsafe_allow_html=True)

        if st.button("Logout", key="logout_btn"):
            try:
                logout(st.session_state['session_id'])
                del st.session_state['session_id']
                del st.session_state['user']
                st.rerun()
            except Exception as e:
                st.error(f"Logout error: {str(e)}")

        menu_options = []
        if has_permission(user['role'], 'dashboard'):
            menu_options.append("Dashboard")
        if has_permission(user['role'], 'inventory'):
            menu_options.append("Inventory")
        if has_permission(user['role'], 'investments'):
            menu_options.append("Investments")
        if has_permission(user['role'], 'expenses'):
            menu_options.append("Expenses")
        if has_permission(user['role'], 'partnership'):
            menu_options.append("Partnership")
        if has_permission(user['role'], 'reports'):
            menu_options.append("Reports")
        if has_permission(user['role'], 'user_management'):
            menu_options.append("User Management")

        menu = st.selectbox("Menu", menu_options, key="main_menu")

    try:
        if menu == "Dashboard":
            show_dashboard()
        elif menu == "Inventory":
            show_inventory()
        elif menu == "Investments":
            show_investments()
        elif menu == "Expenses":
            show_expenses()
        elif menu == "Partnership":
            show_partnership()
        elif menu == "Reports":
            show_reports()
        elif menu == "User Management":
            show_user_management()
    except Exception as e:
        st.error(f"Error loading {menu}: {str(e)}")

if __name__ == "__main__":
    main()