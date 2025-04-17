import streamlit as st
from data.session_state import initialize_session_state
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

# Custom CSS (keep your existing CSS)
st.markdown("""
<style>
    /* Your existing CSS styles */
</style>
""", unsafe_allow_html=True)

def show_login():
    st.title("BizMaster Pro - Login")
    
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
                    st.experimental_rerun()
                else:
                    st.error("Invalid username or password")
            except Exception as e:
                st.error(f"Login error: {str(e)}")

def main():
    # Check for existing session
    if 'session_id' in st.session_state:
        try:
            user = validate_session(st.session_state['session_id'])
            if not user:
                del st.session_state['session_id']
                if 'user' in st.session_state:
                    del st.session_state['user']
                st.experimental_rerun()
            else:
                st.session_state['user'] = user
        except Exception as e:
            st.error(f"Session validation error: {str(e)}")
    
    # Show login if not authenticated
    if 'user' not in st.session_state:
        show_login()
        return
    
    # Main app for authenticated users
    user = st.session_state['user']
    st.title(f"BizMaster Pro - Welcome {user['full_name']} ({user['role'].capitalize()})")
    
    # Initialize business data
    initialize_session_state()
    
    # Sidebar with logout and user info
    with st.sidebar:
        st.markdown(f"**Logged in as:** {user['full_name']}")
        st.markdown(f"**Role:** {user['role'].capitalize()}")
        st.markdown(f"**Business Unit:** {user['business_unit']}")
        
        if st.button("Logout"):
            try:
                logout(st.session_state['session_id'])
                del st.session_state['session_id']
                del st.session_state['user']
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Logout error: {str(e)}")
        
        # Menu options based on permissions
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
        
        if not menu_options:
            st.error("You don't have permissions to access any features")
            return
        
        menu = st.selectbox("Menu", menu_options)
    
    # Main content routing
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

    # Data management in sidebar
    if has_permission(user['role'], 'data_export'):
        st.sidebar.header("Data Management")
        if st.sidebar.button("Export All Data"):
            with st.sidebar.expander("Download Data", expanded=True):
                try:
                    # Your existing export buttons
                    pass
                except Exception as e:
                    st.error(f"Export error: {str(e)}")

    if has_permission(user['role'], 'data_reset'):
        if st.sidebar.button("Reset All Data"):
            if st.sidebar.checkbox("I understand this will delete all data"):
                if st.sidebar.button("Confirm Reset", type="primary"):
                    try:
                        initialize_session_state()
                        st.success("All data has been reset to default values!")
                    except Exception as e:
                        st.error(f"Reset error: {str(e)}")

if __name__ == "__main__":
    main()