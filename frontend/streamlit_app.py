import streamlit as st
import requests
from datetime import datetime
import uuid
import json
import calendar
import re
import os
from dotenv import load_dotenv
from streamlit_feedback import streamlit_feedback

load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
CUSTOM_TOKEN = os.getenv("CUSTOM_TOKEN")

def send_request(endpoint, method="POST", json=None, params=None):
    headers = {"Authorization": f"Bearer {CUSTOM_TOKEN}"}
    url = f"{API_URL}/{endpoint}"
    response = requests.request(method, url, json=json, params=params, headers=headers)
    return response.json() if response.status_code == 200 else None

def send_message(username, message, session_id):
    return send_request("chat/", json={"input": message, "username": username, "session_id": session_id})

def clear_message_history(username, session_id):
    response = send_request("clear_history/", json={"username": username, "session_id": session_id})
    return response is not None

def register_user(username, name, email, password):
    return send_request("register", json={"username": username, "name": name, "email": email, "password": password})

def login_user(username, password):
    return send_request("login", json={"username": username, "password": password})

def folder_selector():
    st.title("Select the Company and the earning calls")
    # Load metadata from the JSON file
    with open("metadata.json", "r") as file:
        metadata = json.load(file)

    # Get unique companies
    unique_companies = list(set([os.path.basename(os.path.dirname(entry["source"])) for entry in metadata]))
    unique_companies.sort()

    # Create a dropdown for selecting the company
    selected_company = st.selectbox("Select a Company:", unique_companies, key="company_selector")

    # Filter metadata based on the selected company
    company_metadata = [entry for entry in metadata if entry["source"].startswith(os.path.join("E:\\earning_reports_copilot\\Concalls", selected_company))]

    years_months = extract_year_month_from_metadata(company_metadata)
    if years_months:
        # Get unique years
        unique_years = list(set([year for year, _ in years_months]))
        unique_years.sort(reverse=True)

        # Create a dropdown for selecting the year
        selected_year = st.selectbox("Select a Year:", unique_years, key="year_selector")

        # Filter years_months based on the selected year
        selected_years_months = [(year, month) for year, month in years_months if year == selected_year]

        if selected_years_months:
            # Get unique months for the selected year
            unique_months = list(set([calendar.month_name[int(month)] for _, month in selected_years_months]))
            unique_months.sort(reverse=True)

            selected_month = st.selectbox("Select Month:", unique_months, key="month_selector")
            selected_paths = []
            for entry in company_metadata:
                if (
                    (selected_month[:3].lower() in entry["source"].lower() or selected_month[:3].upper() in entry["source"].lower()) and
                    (entry["source"].endswith(".pdf") or entry["source"].endswith(".PDF"))
                ):
                    filename_without_date = re.findall(r".*_([^\.]+)\.", entry["source"])[0]
                    path_year = extract_year_from_path(entry["source"])
                    
                    if (
                        filename_without_date in entry["source"].split("\\")[-1] and
                        path_year == selected_year[2:]
                    ):  
                        selected_paths.append(entry["source"])

            return selected_paths

    return []

def extract_year_month_from_metadata(metadata):
    years_months = []
    for entry in metadata:
        match = re.search(r'(\w{3})(\d{2})', entry["source"])
        if match:
            month_abbreviation = match.group(1)
            year_short = match.group(2)

            month_mapping = {
                'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
            }

            month_numeric = month_mapping.get(month_abbreviation.lower())

            if month_numeric:
                year = '20' + year_short
                years_months.append((year, month_numeric))

    return years_months

def extract_year_from_path(path):
    match = re.search(r'(\d{2,4})', path)
    if match:
        return match.group(1)
    else:
        print(f"No year found in path: {path}")
        return None

def send_feedback(username, message_id, feedback_type, score, comment):
    response = requests.post(
        f"{API_URL}/feedback/",
        json={"message_id": message_id, "feedback_type": feedback_type, "score": score, "comment": comment},
        params={"username": username}
    )
    return response.json() if response.status_code == 200 else None

def main():
    st.set_page_config(page_title="Finpro - EarningsWhisperer", page_icon="💹", layout="wide")
    st.title("Finpro - EarningsWhisperer 💹")

    if 'user' not in st.session_state:
        st.session_state.user = {'username': '', 'session_id': ''}

    if not st.session_state.user['username']:
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            st.subheader("Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                user = login_user(username, password)
                if user:
                    st.session_state.user['username'] = user['username']
                    st.session_state.user['session_id'] = user['session_id']
                    st.success("Logged in successfully!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        with tab2:
            st.subheader("Register")
            new_username = st.text_input("Username", key="register_username")
            new_full_name = st.text_input("Full Name", key="register_full_name")
            new_email = st.text_input("Email", key="register_email")
            new_password = st.text_input("Password", type="password", key="register_password")
            if st.button("Register"):
                user = register_user(new_username, new_full_name, new_email, new_password)
                if user:
                    st.session_state.user['username'] = user['username']
                    st.session_state.user['session_id'] = user['session_id']
                    st.success("Registered successfully! You can now log in.")
                    st.rerun()
                else:
                    st.error("Registration failed. Username or email might already exist.")

    else:
        with st.sidebar:
            st.subheader(f"Welcome, {st.session_state.user['username']}!")
            st.session_state.path = folder_selector()

            if st.button("Clear Message History"):
                if clear_message_history(st.session_state.user['username'], st.session_state.user['session_id']):
                    st.session_state.messages = []
                    st.success("Message history cleared successfully.")
                else:
                    st.error("Failed to clear message history.")

            if st.button("Logout"):
                st.session_state.user = {'username': '', 'session_id': ''}
                st.session_state.messages = []
                st.rerun()

        if 'messages' not in st.session_state:
            st.session_state.messages = []

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                if message["role"] == "assistant":
                    feedback = streamlit_feedback(
                        feedback_type="faces",
                        optional_text_label="[Optional] Please provide an explanation",
                        key=f"feedback_{message['id']}",
                    )
                    if feedback:
                        scores = {"😀": 1, "🙂": 0.75, "😐": 0.5, "🙁": 0.25, "😞": 0}
                        feedback_result = send_feedback(
                            st.session_state.user['username'],
                            message['id'],
                            feedback["type"],
                            scores[feedback["score"]],
                            feedback.get("text", None)
                        )
                        if feedback_result:
                            st.toast("Feedback recorded!", icon="📝")
                        else:
                            st.error("Failed to submit feedback.")

        user_input = st.chat_input("What would you like to know about the earnings call?")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            with st.spinner("Thinking..."):
                response = send_message(st.session_state.user['username'], user_input, st.session_state.user['session_id'])
                if response:
                    assistant_response = response['response']
                    message_id = response['message_id']
                    st.session_state.messages.append({"role": "assistant", "content": assistant_response, "id": message_id})
                    with st.chat_message("assistant"):
                        st.markdown(assistant_response)
                    
                    # Display metrics
                    if 'metrics' in response and response['metrics']:
                        st.subheader("Response Metrics")
                        st.table(response['metrics'])
                else:
                    st.error("Failed to get response from the assistant.")

if __name__ == "__main__":
    main()