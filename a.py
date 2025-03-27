import streamlit as st
import pandas as pd
import sqlite3
import qrcode
from PIL import Image
import io
import datetime
from datetime import timedelta

# Database setup (our digital filing cabinet 📂)
conn = sqlite3.connect('cdams.db', check_same_thread=False)
c = conn.cursor()

# Setting up tables 🗄️
c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY, 
    password TEXT, 
    role TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY, 
    name TEXT, 
    location TEXT, 
    status TEXT, 
    last_maintenance DATE, 
    next_maintenance DATE, 
    warranty_expiry DATE, 
    cost REAL)''')
c.execute('''CREATE TABLE IF NOT EXISTS logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT, 
    asset_id TEXT, 
    action TEXT, 
    user TEXT, 
    timestamp TEXT)''')
conn.commit()

# Default users 👩‍💼👨‍💼
sample_users = [
    ("admin", "admin123", "Executive"),
    ("finance", "fin123", "Finance"),
    ("ops", "ops123", "Operations"),
    ("user", "user123", "User")
]
for user in sample_users:
    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", user)
conn.commit()

# Permissions for each role 🔑
role_permissions = {
    "Executive": ["view_all", "analytics", "manage_assets", "view_logs", "track_assets", "view_costs", "request_maintenance"],
    "Finance": ["manage_assets", "view_costs", "request_maintenance"],
    "Operations": ["manage_assets", "track_assets", "request_maintenance"],
    "User": ["view_assets", "request_maintenance"]
}

# Helper functions 🤖
def check_login(username, password):
    c.execute("SELECT password, role FROM users WHERE username=?", (username,))
    result = c.fetchone()
    if result and result[0] == password:
        return result[1]
    return None

def get_assets():
    df = pd.read_sql_query("SELECT * FROM assets", conn)
    for col in ["last_maintenance", "next_maintenance", "warranty_expiry"]:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    return df

def log_action(asset_id, action, user):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO logs (asset_id, action, user, timestamp) VALUES (?, ?, ?, ?)", 
              (asset_id, action, user, timestamp))
    conn.commit()

# Streamlit App 🎉
st.title("Centralized Digital Asset Management System (CDAMS) 🌟")
st.write("Welcome! Manage your stuff easily with this fun tool! 😊")

# Session state for login 🕵️
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None

# Login Page 🚪
if not st.session_state.logged_in:
    st.subheader("Login Time! 🔐")
    st.write("Enter your details to jump in! 👇")
    username = st.text_input("Your Username", help="Try 'admin' or 'user' 😎")
    password = st.text_input("Your Password", type="password", help="Keep it secret! 🤫")
    if st.button("Login 🚀"):
        role = check_login(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.role = role
            st.session_state.username = username
            st.success(f"Yay! You're in as {username} ({role}) 🎉")
        else:
            st.error("Oops! Wrong details 😕 Try again!")

# Main App 🎈
if st.session_state.logged_in:
    st.sidebar.subheader(f"Hello, {st.session_state.username}! 👋")
    st.sidebar.write(f"You're a {st.session_state.role}! Awesome! 😎")
    if st.sidebar.button("Logout 👋"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = None
        st.rerun()  # Updated from st.experimental_rerun()

    # All tabs with permissions
    all_tabs = {
        "Assets 🗃️": "view_assets",
        "Track Asset 📍": "track_assets",
        "Analytics 📊": "analytics",
        "Costs 💰": "view_costs",
        "Logs 📜": "view_logs",
        "Maintenance 🛠️": "request_maintenance"
    }

    # Filter tabs strictly based on permissions, ensuring Assets is always included
    permissions = role_permissions[st.session_state.role]
    visible_tabs = [tab for tab, perm in all_tabs.items() if perm in permissions or "view_all" in permissions]
    if "Assets 🗃️" not in visible_tabs:  # Ensure Assets tab is always present
        visible_tabs.insert(0, "Assets 🗃️")  # Add at the start if missing
    tabs = st.tabs(visible_tabs)

    # Assets Tab 🗃️ (always present due to the above logic)
    with tabs[visible_tabs.index("Assets 🗃️")]:
        st.subheader("Your Stuff 🗃️")
        st.write("Here’s all your gear! 👀")
        assets_df = get_assets()
        st.dataframe(assets_df)
        
        if "manage_assets" in permissions:
            st.write("Add or update your gear here! ✏️")
            with st.form("add_asset"):
                asset_id = st.text_input("Asset ID", help="A special code, like 'LAP001' 🔢")
                name = st.text_input("What’s it called?", help="Like 'Laptop' or 'Machine' 📛")
                location = st.text_input("Where is it?", help="Like 'Office' or 'Warehouse' 📍")
                status = st.selectbox("How’s it doing?", ["Active ✅", "Maintenance 🛠️", "Retired 🏁"])
                last_maintenance = st.date_input("Last Check-Up", help="When was it last fixed? 🗓️")
                next_maintenance = st.date_input("Next Check-Up", help="When’s it due next? ⏰")
                warranty_expiry = st.date_input("Warranty Ends", help="When’s the warranty up? 📅")
                cost = st.number_input("How much did it cost?", min_value=0.0, help="In rupees ₹")
                if st.form_submit_button("Add It! ➕"):
                    c.execute("INSERT OR REPLACE INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                              (asset_id, name, location, status.split(" ")[0], last_maintenance, next_maintenance, warranty_expiry, cost))
                    conn.commit()
                    log_action(asset_id, "Added/Updated", st.session_state.username)
                    st.success("Sweet! Your gear is added/updated! 🎉")

    # Track Asset Tab 📍
    if "Track Asset 📍" in visible_tabs:
        with tabs[visible_tabs.index("Track Asset 📍")]:
            st.subheader("Find Your Stuff! 📍")
            st.write("Create a QR code with all the details of your gear! 🖼️")
            asset_id = st.text_input("Enter Asset ID", help="Type the code of your gear 🔍")
            if st.button("Make QR Code! 🖌️"):
                if asset_id:
                    # Fetch the asset details from the database
                    assets_df = get_assets()
                    asset = assets_df[assets_df["asset_id"] == asset_id]
                    if not asset.empty:
                        # Create a string with all asset info (using ₹ for cost)
                        asset_info = (
                            f"Asset ID: {asset['asset_id'].iloc[0]}\n"
                            f"Name: {asset['name'].iloc[0]}\n"
                            f"Location: {asset['location'].iloc[0]}\n"
                            f"Status: {asset['status'].iloc[0]}\n"
                            f"Last Maintenance: {asset['last_maintenance'].iloc[0]}\n"
                            f"Next Maintenance: {asset['next_maintenance'].iloc[0]}\n"
                            f"Warranty Expiry: {asset['warranty_expiry'].iloc[0]}\n"
                            f"Cost: ₹{asset['cost'].iloc[0]:.2f}"
                        )
                        # Generate QR code with full info
                        qr = qrcode.QRCode(version=1, box_size=10, border=5)
                        qr.add_data(asset_info)
                        qr.make(fit=True)
                        img = qr.make_image(fill_color="black", back_color="white")
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        buf.seek(0)
                        st.image(buf.getvalue(), caption=f"QR Code for {asset_id} 🌟", use_container_width=True)
                        log_action(asset_id, "Tracked", st.session_state.username)
                        st.write("Scan this with your phone to see all details! 📱")
                    else:
                        st.error("Oops! No gear found with that ID! 😕")
                else:
                    st.error("Oops! Enter an Asset ID first! 😕")

    # Analytics Tab 📊
    if "Analytics 📊" in visible_tabs:
        with tabs[visible_tabs.index("Analytics 📊")]:
            st.subheader("Cool Stats! 📊")
            st.write("Check how your gear is doing! 📈")
            assets_df = get_assets()
            st.bar_chart(assets_df.groupby("status").size(), use_container_width=True)
            st.write("See how many are active, in repair, or retired! 🧐")
            st.line_chart(assets_df[["cost"]], use_container_width=True)
            st.write("Here’s the cost of your gear over time! 💸")

    # Costs Tab 💰
    if "Costs 💰" in visible_tabs:
        with tabs[visible_tabs.index("Costs 💰")]:
            st.subheader("Money Talk! 💰")
            st.write("See what your gear costs! 🤑")
            assets_df = get_assets()
            total_cost = assets_df["cost"].sum()
            st.metric("Total Cost", f"₹{total_cost:,.2f}", help="All your gear added up! ₹")
            st.dataframe(assets_df[["asset_id", "name", "cost"]])

    # Logs Tab 📜
    if "Logs 📜" in visible_tabs:
        with tabs[visible_tabs.index("Logs 📜")]:
            st.subheader("What’s Been Happening? 📜")
            st.write("Track every move! 🕵️")
            logs_df = pd.read_sql_query("SELECT * FROM logs", conn)
            st.dataframe(logs_df)

    # Maintenance Tab 🛠️
    if "Maintenance 🛠️" in visible_tabs:
        with tabs[visible_tabs.index("Maintenance 🛠️")]:
            st.subheader("Fix It Up! 🛠️")
            st.write("Keep your gear in tip-top shape! 🔧")
            assets_df = get_assets()
            today = datetime.date.today()
            upcoming = assets_df[assets_df["next_maintenance"].notna() & 
                                (assets_df["next_maintenance"] <= pd.Timestamp(today + timedelta(days=7)))]
            st.write("Gear needing a check-up soon (next 7 days): ⏰")
            st.dataframe(upcoming)
            
            if "request_maintenance" in permissions or "manage_assets" in permissions:
                with st.form("maintenance_request"):
                    asset_id = st.text_input("Asset ID to Fix", help="Which gear needs help? 🔍")
                    if st.form_submit_button("Ask for Fix! 🔔"):
                        c.execute("UPDATE assets SET status='Maintenance' WHERE asset_id=?", (asset_id,))
                        conn.commit()
                        log_action(asset_id, "Maintenance Requested", st.session_state.username)
                        st.success("Fix request sent! Someone’s on it! 🚀")

    # Alerts! 🚨
    st.subheader("Heads Up! 🚨")
    assets_df = get_assets()
    for index, row in assets_df.iterrows():
        if pd.notna(row["next_maintenance"]) and row["next_maintenance"] <= pd.Timestamp(today) and row["status"] != "Maintenance":
            st.warning(f"⚠️ Fix {row['name']} (ID: {row['asset_id']}) now! It’s due!")
        if pd.notna(row["warranty_expiry"]) and row["warranty_expiry"] <= pd.Timestamp(today + timedelta(days=30)):
            st.warning(f"⏳ Warranty for {row['name']} (ID: {row['asset_id']}) ends soon!")

# Exit button 🚪
if st.button("All Done? Exit! 👋"):
    conn.close()
    st.success("See you next time! 😊")
    st.stop()