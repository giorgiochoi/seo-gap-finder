import streamlit as st
import requests
import os
from firecrawl import Firecrawl
from google import genai

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍", layout="wide")

# Fetch keys from Streamlit Secrets
gemini_key = st.secrets.get("GEMINI_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY")
serper_key = st.secrets.get("SERPER_API_KEY")
# PASTE YOUR WEBHOOK URL HERE
WEBHOOK_URL = "https://hook.us2.make.com/i4ntiyak1rrawyvbfvrbe1y73vgg44ia" 

if not all([gemini_key, firecrawl_key, serper_key]):
    st.error("Missing API keys in Streamlit Secrets.")
    st.stop()

# Initialize SDKs
firecrawl = Firecrawl(api_key=firecrawl_key)
client = genai.Client(api_key=gemini_key, http_options={'api_version': 'v1beta'})

# --- 2. STATE MANAGEMENT ---
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# --- 3. UI LAYOUT ---
st.title("🔍 SEO Content Gap Finder")

with st.sidebar:
    st.header("Project Settings")
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword", placeholder="luxury watches")
    run_btn = st.button("Run AI Analysis", use_container_width=True)

# --- 4. CORE LOGIC ---
if run_btn:
    if not user_url or not target_keyword:
        st.warning("Please provide both a URL and a keyword.")
    else:
        try:
            # STEP 1: Find Competitor via Serper
            with st.spinner("🕵️ Searching for top competitor..."):
                headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                search_res = requests.post(
                    'https://google.serper.dev/search', 
                    json={"q": target_keyword, "num": 1}, 
                    headers=headers
                )
                search_data = search_res.json()
                
                if 'organic' not in search_data or not search_data['organic']:
                    st.error("No search results found.")
                    st.stop()
                
                comp_url = search_data['organic'][0]['link'].split('?')[0]
                st.session_state.current_comp = comp_url

           # STEP 2: Scrape both sites
            with st.spinner("📄 Scraping content..."):
                # Updated to the latest Firecrawl SDK syntax
                user_scrape = firecrawl.scrape(user_url, formats=['markdown'])
                comp_scrape = firecrawl.scrape(comp_url, formats=['markdown'])
                
                # Extract markdown, providing an empty string if it fails
                u_md = getattr(user_scrape, 'markdown', "")[:8000]
                c_md = getattr(comp_scrape, 'markdown', "")[:8000]

            # STEP 3: Gemini Analysis
            with st.spinner("♊ Gemini 3 is analyzing..."):
                prompt = f"""
                Compare these sites for '{target_keyword}'.
                USER: {u_md}
                COMPETITOR: {c_md}
                Output 3 specific gaps and an execution plan. Use markdown.
                """
                response = client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=prompt
                )
                
                st.session_state.report_content = response.text
                st.session_state.report_ready = True
                st.session_state.current_url = user_url
                st.session_state.current_keyword = target_keyword

        except Exception as e:
            st.error(f"Analysis failed: {e}")

# --- 5. DISPLAY & LEAD CAPTURE ---
if st.session_state.report_ready:
    st.divider()
    st.subheader("📊 The Content Gap Report")
    st.markdown(st.session_state.report_content)
    
    st.divider()
    # Use a form to prevent double-firing and organize inputs
    with st.form("lead_capture_form", clear_on_submit=True):
        st.subheader("📬 Get the Full Strategy PDF")
        email_input = st.text_input("Email Address")
        submit_lead = st.form_submit_button("Send Me the Report")
        
        if submit_lead:
            if "@" not in email_input:
                st.error("Invalid email address.")
            else:
                # Basic Markdown to HTML conversion for Google Docs compatibility
                clean_summary = st.session_state.report_content.replace("**", "<b>").replace("### ", "<h3>")
                
                payload = {
                    "email": email_input, 
                    "url": st.session_state.current_url, 
                    "keyword": st.session_state.current_keyword,
                    "summary": clean_summary
                }
                
                try:
                    # Final sanity check on URL
                    if not WEBHOOK_URL.startswith("http"):
                        st.error("WEBHOOK_URL is missing 'https://'")
                    else:
                        response = requests.post(WEBHOOK_URL, json=payload)
                        if response.status_code == 200:
                            st.balloons()
                            st.success(f"Success! Report sent to {email_input}")
                        else:
                            st.error(f"Make.com error: {response.status_code}")
                except Exception as e:
                    st.error(f"Connection error: {e}")
