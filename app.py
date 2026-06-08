import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import urllib.parse
import requests
import os

# Page Setup
st.set_page_config(page_title="Smart Saver AI", page_icon="💰", layout="wide")

# --- MULTI-USER STORAGE DATABASE SYSTEM ---
DB_FILE = "master_ledger.csv"

# Function to load database from a permanent file
def load_global_database():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE, dtype={"User Phone": str, "Friend Phone": str})
    else:
        return pd.DataFrame(
            columns=["Date", "User Phone", "Type", "Category", "Amount (Rs)", "Friend Name", "Friend Phone", "Comments"]
        )

# Function to save database back to the permanent file
def save_to_global_database(df):
    df.to_csv(DB_FILE, index=False)

# Initialize global storage memory
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {"name": "", "phone": ""}

# Sidebar Configuration
st.sidebar.header("🔑 API Keys Configuration")
gemini_key = st.sidebar.text_input("1. Enter Gemini API Key:", type="password")
sms_key = st.sidebar.text_input("2. Enter Fast2SMS API Key:", type="password")

# SMS Sending Engine
def send_real_sms(api_key, phone_number, friend_name, amount, item_comment):
    url = "https://www.fast2sms.com/dev/bulkV2"
    message = f"Hi {friend_name}, reminder! You owe me {amount} Rs for '{item_comment}'. Please refund it when free."
    payload = {"message": message, "language": "english", "route": "q", "numbers": phone_number}
    headers = {'authorization': api_key, 'Content-Type': "application/x-www-form-urlencoded"}
    try:
        response = requests.post(url, data=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"return": False, "message": str(e)}

# Onboarding Profile Screen
if not st.session_state.user_profile["name"]:
    st.title("🚀 Smart Saver Multi-User Portal")
    st.write("Enter your phone number to access your unique spending dashboard.")
    
    with st.form("profile_form"):
        reg_name = st.text_input("Your Name:")
        reg_phone = st.text_input("Your Mobile Number (10 digits):")
        submit_profile = st.form_submit_button("Access My Account")
        
        if submit_profile:
            if reg_name and len(reg_phone) >= 10:
                st.session_state.user_profile = {"name": reg_name, "phone": reg_phone.strip()}
                st.rerun()
            else:
                st.warning("Please enter a valid name and a 10-digit mobile number.")
else:
    # Fetch user details
    user_name = st.session_state.user_profile["name"]
    user_phone = st.session_state.user_profile["phone"]
    
    st.title(f"💰 Smart Saver Dashboard — Active User: {user_name} ({user_phone})")
    
    if st.button("🚪 Log Out / Change Number"):
        st.session_state.user_profile = {"name": "", "phone": ""}
        st.rerun()
        
    if not gemini_key:
        st.info("Please enter your Gemini API key in the sidebar to activate your custom environment.")
    else:
        genai.configure(api_key=gemini_key)

        # Log Input UI
        st.subheader("🖋️ Log a New Transaction")
        col_type, col_cat, col_amt = st.columns(3)
        col_friend, col_fphone, col_cmt = st.columns([2, 2, 4])
        
        with col_type:
            tx_type = st.selectbox("Transaction Type:", ["Expense/Lent (Outflow)", "Borrowed (Inflow)"])
        with col_cat:
            category = st.selectbox("Category:", ["Meals", "Travel", "Friends/Loans", "Rents", "Purchase", "Grocery", "Fuel"])
        with col_amt:
            amount = st.number_input("Amount (Rs):", min_value=0.0, step=10.0)
            
        with col_friend:
            friend_name = st.text_input("Friend's Name:")
        with col_fphone:
            friend_phone = st.text_input("Friend's Mobile No. (10 digits):")
        with col_cmt:
            comment = st.text_input("Comments/Notes:")

        if st.button("Save Entry"):
            if amount > 0:
                current_date = datetime.now().strftime("%Y-%m-%d")
                
                # Load the full master database file
                master_df = load_global_database()
                
                # Append the new row containing this specific user's phone number
                new_row = pd.DataFrame([{
                    "Date": current_date,
                    "User Phone": user_phone,  # Locked to this specific account number
                    "Type": tx_type,
                    "Category": category,
                    "Amount (Rs)": amount,
                    "Friend Name": friend_name if friend_name else "N/A",
                    "Friend Phone": friend_phone if friend_phone else "",
                    "Comments": comment if comment else "None"
                }])
                
                master_df = pd.concat([master_df, new_row], ignore_index=True)
                save_to_global_database(master_df)
                st.success("Entry securely saved to your phone number account records!")
            else:
                st.warning("Please enter a valid amount.")

        # --- LOAD AND FILTER ROWS SPECIFICALLY FOR THIS MOBILE NUMBER ---
        global_df = load_global_database()
        user_filtered_df = global_df[global_df["User Phone"] == user_phone]
        
        if not user_filtered_df.empty:
            st.markdown("---")
            st.subheader(f"📅 Personal Ledger for {user_phone}")
            
            for index, row in user_filtered_df.iterrows():
                with st.expander(f"📌 [{row['Date']}] {row['Type']} - {row['Category']}: {row['Amount (Rs)']} Rs"):
                    st.write(f"**Details:** {row['Comments']} | **Friend:** {row['Friend Name']}")
                    
                    if row['Type'] == "Expense/Lent (Outflow)" and pd.notna(row['Friend Phone']) and str(row['Friend Phone']) != "":
                        btn_col1, btn_col2 = st.columns(2)
                        with btn_col1:
                            msg = f"Hey {row['Friend Name']}, you owe me {row['Amount (Rs)']} Rs for '{row['Comments']}'."
                            wa_link = f"https://wa.me/91{row['Friend Phone']}?text={urllib.parse.quote(msg)}"
                            st.markdown(f"[💬 Send WhatsApp Reminder]({wa_link})")
                        with btn_col2:
                            if st.button("📱 Send Carrier SMS", key=f"sms_{index}"):
                                if not sms_key:
                                    st.warning("Provide your Fast2SMS key in the sidebar first!")
                                else:
                                    with st.spinner("Processing carrier text..."):
                                        result = send_real_sms(sms_key, row['Friend Phone'], row['Friend Name'], row['Amount (Rs)'], row['Comments'])
                                        if result.get("return"):
                                            st.success("📱 Text sent successfully!")
                                        else:
                                            st.error("Failed to drop SMS. Check credits.")
            
            # Graphs isolated to current user data
            st.markdown("---")
            st.subheader("📊 Your Private Financial Analytics")
            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.write("Your Inflow vs Outflow")
                st.bar_chart(user_filtered_df.groupby("Type")["Amount (Rs)"].sum())
            with chart_col2:
                st.write("Your Spending Breakdown")
                st.bar_chart(user_filtered_df.groupby("Category")["Amount (Rs)"].sum())
        else:
            st.info("No records found for this phone number yet. Log your first expense above!")
