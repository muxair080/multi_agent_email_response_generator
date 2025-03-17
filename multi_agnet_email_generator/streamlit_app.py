import streamlit as st
import time
from mutli_agent_email_response_genrator import generate_final_response
# Dummy function to simulate chatbot response (Replace with your actual function)

# Streamlit App
st.set_page_config(page_title="AI Email Replies Generator", page_icon="📧", layout="centered")

# Custom CSS for styling
st.markdown("""
    <style>
        .main {background-color: #f0f2f6;}
        .stTextInput input {border-radius: 10px; font-size: 16px;}
        .stButton>button {border-radius: 10px; background: #4CAF50; color: white; font-size: 16px; padding: 10px 24px;}
        .stMarkdown {font-size: 16px;}
        .chat-container {background: black; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);}
    </style>
""", unsafe_allow_html=True)

# App Title
st.title("📧 AI Email ReplyPro Generator")

# User input field
user_input = st.text_area("Enter your prompt:", placeholder="E.g., Request for a meeting...")

# Submit Button
if st.button("Generate Email Reply"):
    if user_input.strip() == "":
        st.warning("⚠️ Please enter a valid prompt.")
    else:
        with st.spinner("Generating email reply... ✨"):
            response = generate_final_response(user_input)
            st.success("✅ Email reply generated!")
            st.markdown(f"<div class='chat-container'>{response}</div>", unsafe_allow_html=True)

# Footer
st.markdown("<br><p style='text-align: center; color: gray;'>🚀 Built with Streamlit</p>", unsafe_allow_html=True)
