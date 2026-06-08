import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import urllib.parse
import requests  # New library for sending SMS

# Page Setup
st.set_page_config(page_title="Smart Saver AI", page_icon="💰", layout="wide")

# Initialize State Memory
if "expense_db" not in st.session_state:
    st.session_state.expense_db = pd.DataFrame(
        columns=["Date", "Type", "Category", "Amount (Rs)", "Friend Name", "Phone", "Comments"]
    )
if "user_profile" not in st.session_state:
    st.session_state.user_profile = {"name": "", "phone": ""}

# Sidebar Configuration
st.sidebar.header("🔑 API Keys Configuration")
gemini_key = st.sidebar.text_input("1. Enter Gemini API Key:", type="password")
sms_key = st.sidebar.text_input("2. Enter Fast2SMS API Key:", type="password")

# --- SMS SENDING FUNCTION ---
def send_real_sms(api_key, phone_number, friend_name, amount, item_comment):
    url = "https://www.fast2sms.com/dev/bulkV2"
    message = f"Hi {friend_name}, friendly reminder! You owe me {amount} Rs for '{item_comment}'. Please refund it when free."
    
    payload = {
        "message": message,
        "language": "english",
        "route": "q",
        "numbers": phone_number
    }
    headers = {
        'authorization': api_key,
        'Content-Type': "application/x-www-form-urlencoded"
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        return response.json()
    except Exception as e:
        return {"return": False, "message": str(e)}


# Profile Onboarding Screen
if not st.session_state.user_profile["name"]:
    st.title("🚀 Welcome to Smart Saver AI")
    with st.form("profile_form"):
        reg_name = st.text_input("Your Name:")
        reg_phone = st.text_input("Your Mobile Number:")
        submit_profile = st.form_submit_button("Start Saving")
        if submit_profile and reg_name and reg_phone:
            st.session_state.user_profile = {"name": reg_name, "phone": reg_phone}
            st.rerun()
else:
    # MAIN APP INTERFACE
    st.title(f"💰 Smart Saver Dashboard — Welcome, {st.session_state.user_profile['name']}!")
    
    if not gemini_key:
        st.info("Please enter your Gemini API key in the sidebar to activate the AI Coach.")
    else:
        genai.configure(api_key=gemini_key)

        # Form Input UI
        st.subheader("🖋️ Log a Transaction")
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
                new_row = pd.DataFrame([{
                    "Date": current_date,
                    "Type": tx_type,
                    "Category": category,
                    "Amount (Rs)": amount,
                    "Friend Name": friend_name if friend_name else "N/A",
                    "Phone": friend_phone if friend_phone else "",
                    "Comments": comment if comment else "None"
                }])
                st.session_state.expense_db = pd.concat([st.session_state.expense_db, new_row], ignore_index=True)
                st.success("Entry recorded successfully!")
            else:
                st.warning("Please enter a valid amount.")

        # Display Ledger & Actions
        df = st.session_state.expense_db
        if not df.empty:
            st.markdown("---")
            st.subheader("📅 Financial Ledger & Reminders")
            
            for index, row in df.iterrows():
                with st.expander(f"📌 [{row['Date']}] {row['Type']} - {row['Category']}: {row['Amount (Rs)']} Rs"):
                    st.write(f"**Details:** {row['Comments']} | **Friend:** {row['Friend Name']} ({row['Phone']})")
                    
                    if row['Type'] == "Expense/Lent (Outflow)" and row['Phone'] != "":
                        # Action column layouts
                        btn_col1, btn_col2 = st.columns(2)
                        
                        with btn_col1:
                            # WhatsApp Fallback Link
                            msg = f"Hey {row['Friend Name']}, you owe me {row['Amount (Rs)']} Rs for '{row['Comments']}'."
                            wa_link = f"https://wa.me/91{row['Phone']}?text={urllib.parse.quote(msg)}"
                            st.markdown(f"[💬 Send WhatsApp Reminder]({wa_link})")
                            
                        with btn_col2:
                            # Real Mobile SMS Trigger Button
                            if st.button("📱 Send Carrier SMS", key=f"sms_{index}"):
                                if not sms_key:
                                    st.warning("Please provide your Fast2SMS key in the sidebar first!")
                                else:
                                    with st.spinner("Sending carrier SMS text..."):
                                        result = send_real_sms(sms_key, row['Phone'], row['Friend Name'], row['Amount (Rs)'], row['Comments'])
                                        if result.get("return"):
                                            st.success("📱 Real SMS text dropped directly into their phone inbox!")
                                        else:
                                            st.error(f"Failed to send SMS: {result.get('message', 'Check API credits')}")