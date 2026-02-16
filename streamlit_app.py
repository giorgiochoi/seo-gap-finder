import streamlit as st
import requests
import re
import os
from firecrawl import Firecrawl
from google import genai

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍", layout="wide")

# Fetch keys from Streamlit Secrets
gemini_key = st.secrets.get("GEMINI_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY")
serper_key = st.secrets.get("SERPER_API_KEY")
# Ensure this URL starts with https://
WEBHOOK_URL = "https://hook.us2.make.com/your_unique_id_here" 

if not all([gemini_key, firecrawl_key, serper_key]):
    st.error("Missing API keys in Streamlit Secrets.")
    st.stop()

# Initialize SDKs
firecrawl = Firecrawl(api_key=firecrawl_key)
client = genai.Client(api_key=gemini_key, http_options={'api_version': 'v1beta'})

# --- 2. FORMATTING HELPER ---
def markdown_to_safe_html(text):
    """Converts basic markdown to closed HTML tags to prevent font-scaling issues."""
    # Convert ### Headers
    text = re.sub(r'### (.*?)\n', r'<h3>\1</h3>', text)
    # Convert **Bold**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Convert newlines to breaks
    text = text.replace('\n', '<br>')
    # Wrap in a fixed-size div to reset email client scaling
    return f"<div style='font-size:14px; font-family:sans-serif; line-height:1.6;'>{text}</div>"

# --- 3. STATE MANAGEMENT ---
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# --- 4. UI LAYOUT ---
st.title("🔍 SEO Content Gap Finder")

with st.sidebar:
    st.header("Project Settings")
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword", placeholder="luxury watches")
    run_btn = st.button("Run AI Analysis", use_container_width=True)

# --- 5. CORE LOGIC ---
if run_btn:
    if not user_url or not target_keyword:
        st.warning("Please provide both a URL and a keyword.")
    else:
        try:
            # STEP 1: Find Competitor
            with st.spinner("🕵️ Searching for top competitor..."):
                headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                search_res = requests.post('https://google.serper.dev/search', 
                                         json={"q": target_keyword, "num": 1}, headers=headers)
                comp_url = search_res.json()['organic'][0]['link'].split('?')[0]
                st.session_state.current_comp = comp_url

            # STEP 2: Scrape (Updated Firecrawl Syntax)
            with st.spinner("📄 Scraping content..."):
                user_scrape = firecrawl.scrape(user_url, formats=['markdown'])
                comp_scrape = firecrawl.scrape(comp_url, formats=['markdown'])
                u_md = getattr(user_scrape, 'markdown', "")[:8000]
                c_md = getattr(comp_scrape, 'markdown', "")[:8000]

            # STEP 3: Gemini Analysis
            with st.spinner("♊ Gemini is analyzing..."):
                prompt = f"Compare {user_url} vs {comp_url} for '{target_keyword}'. Output 3 gaps and a plan. Use markdown."
                response = client.models.generate_content(model='gemini-3-flash-preview', contents=prompt)
                
                st.session_state.report_content = response.text
                st.session_state.report_ready = True
                st.session_state.current_url = user_url
                st.session_state.current_keyword = target_keyword

        except Exception as e:
            st.error(f"Analysis failed: {e}")

# --- 6. DISPLAY & LEAD CAPTURE ---
if st.session_state.report_ready:
    st.divider()
    st.subheader("📊 The Content Gap Report")
    st.markdown(st.session_state.report_content)
    
    st.divider()
    with st.form("lead_capture_form", clear_on_submit=True):
        st.subheader("📬 Get the Full Strategy PDF")
        email_input = st.text_input("Email Address")
        submit_lead = st.form_submit_button("Send Me the Report")
        
        if submit_lead:
            if "@" not in email_input:
                st.error("Invalid email address.")
            else:
                # Use the helper to fix formatting before sending
                html_summary = markdown_to_safe_html(st.session_state.report_content)
                
                payload = {
                    "email": email_input, 
                    "url": st.session_state.current_url, 
                    "keyword": st.session_state.current_keyword,
                    "summary": html_summary 
                }
                
                try:
                    res = requests.post(WEBHOOK_URL, json=payload)
                    if res.status_code == 200:
                        st.balloons()
                        st.success(f"Success! Check {email_input} shortly.")
                    else:
                        st.error(f"Make.com error: {res.status_code}")
                except Exception as e:
                    st.error(f"Connection error: {e}")
