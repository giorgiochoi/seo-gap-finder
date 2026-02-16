import streamlit as st
import requests
import os
from firecrawl import Firecrawl
from langchain_anthropic import ChatAnthropic

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍", layout="wide")

# Fetch keys from Streamlit Secrets
anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY")
serper_key = st.secrets.get("SERPER_API_KEY")

if not all([anthropic_key, firecrawl_key, serper_key]):
    st.error("Missing API keys. Please check your Streamlit Secrets.")
    st.stop()

# Initialize SDKs (Using modern Firecrawl class)
firecrawl = Firecrawl(api_key=firecrawl_key)
model = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=anthropic_key)

# --- 2. STATE MANAGEMENT ---
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# --- 3. UI LAYOUT ---
st.title("🔍 SEO Content Gap Finder")
st.markdown("Enter your URL and a keyword to find exactly what your top competitor is outranking you on.")

with st.sidebar:
    st.header("Project Settings")
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword", placeholder="best wireless headphones")
    run_btn = st.button("Run AI Analysis", use_container_width=True)

# --- 4. CORE LOGIC ---
if run_btn:
    if not user_url or not target_keyword:
        st.warning("Please provide both a URL and a keyword.")
    else:
        with st.spinner("🕵️ Searching for top competitor via Serper.dev..."):
            try:
                # STEP 1: Find Competitor via Serper
                headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                search_res = requests.post(
                    'https://google.serper.dev/search', 
                    json={"q": target_keyword, "num": 1}, 
                    headers=headers
                )
                search_data = search_res.json()
                
                if 'organic' not in search_data or not search_data['organic']:
                    st.error("No search results found. Check your Serper API key or keyword.")
                    st.stop()
                
                # Clean the competitor URL (removes tracking parameters)
                comp_url = search_data['organic'][0]['link'].split('?')[0]
                st.info(f"Targeting Competitor: {comp_url}")

                # STEP 2: Scrape both sites (Updated to latest Firecrawl SDK)
                with st.spinner("📄 Scraping content..."):
                    # The latest SDK uses .scrape() and returns a Document object
                    user_scrape = firecrawl.scrape(user_url, params={'formats': ['markdown']})
                    comp_scrape = firecrawl.scrape(comp_url, params={'formats': ['markdown']})
                    
                    # Access the markdown content from the document object
                    user_markdown = user_scrape.get('markdown', '') if isinstance(user_scrape, dict) else getattr(user_scrape, 'markdown', '')
                    comp_markdown = comp_scrape.get('markdown', '') if isinstance(comp_scrape, dict) else getattr(comp_scrape, 'markdown', '')

                # STEP 3: AI Gap Analysis
                if not user_markdown or not comp_markdown:
                    st.error("Could not extract enough content to analyze. One of the sites may be blocking the scraper.")
                    st.stop()

                with st.spinner("🤖 Claude is analyzing the gap..."):
                    prompt = (
                        f"Compare the content of {user_url} against the top-ranking competitor {comp_url} "
                        f"for the keyword '{target_keyword}'. \n\n"
                        f"USER SITE CONTENT: {user_markdown[:8000]}\n\n"
                        f"COMPETITOR CONTENT: {comp_markdown[:8000]}\n\n"
                        "Provide a professional 'Content Gap Report'. List 3 specific sub-topics the competitor covers "
                        "that the user is missing, and provide a 200-word execution plan to outrank them."
                    )
                    response = model.invoke(prompt)
                    
                    st.session_state.report_content = response.content
                    st.session_state.report_ready = True
                    st.session_state.current_url = user_url
                    st.session_state.current_keyword = target_keyword
                    
            except Exception as e:
                st.error(f"An error occurred: {e}")

# --- 5. DISPLAY & LEAD CAPTURE ---
if st.session_state.report_ready:
    st.divider()
    st.subheader("📊 The Gap Report")
    st.markdown(st.session_state.report_content)
    
    st.divider()
    st.subheader("📬 Get the Full 10-Page Strategy")
    with st.form("lead_capture"):
        email = st.text_input("Email Address")
        submit_lead = st.form_submit_button("Send Me the Full Report")
        
        if submit_lead:
            if "@" not in email:
                st.error("Please enter a valid email.")
            else:
                webhook_url = "https://hook.us2.make.com/i4ntiyak1rrawyvbfvrbe1y73vgg44ia"
                payload = {
                    "email": email, 
                    "url": st.session_state.current_url, 
                    "keyword": st.session_state.current_keyword
                }
                requests.post(webhook_url, json=payload)
                st.balloons()
                st.success("Success! Your full strategy will arrive in your inbox shortly.")
