import streamlit as st
import requests
from firecrawl import Firecrawl
from google import genai
from google.genai import types

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍", layout="wide")

# Fetch keys from Streamlit Secrets
gemini_key = st.secrets.get("GEMINI_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY")
serper_key = st.secrets.get("SERPER_API_KEY")

if not all([gemini_key, firecrawl_key, serper_key]):
    st.error("Missing API keys. Please add GEMINI_API_KEY, FIRECRAWL_API_KEY, and SERPER_API_KEY to your Streamlit Secrets.")
    st.stop()

# Initialize SDKs
# v1beta is required for the 2026 'Gemini 3' preview models
firecrawl = Firecrawl(api_key=firecrawl_key)
client = genai.Client(api_key=gemini_key, http_options={'api_version': 'v1beta'})

# --- 2. STATE MANAGEMENT ---
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# --- 3. UI LAYOUT ---
st.title("🔍 SEO Content Gap Finder")
st.markdown("Compare your site against the top competitor for any keyword.")

with st.sidebar:
    st.header("Project Settings")
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword", placeholder="luxury watches")
    run_btn = st.button("Run AI Analysis", use_container_width=True)
    
    st.divider()
    st.info("Using Gemini 3 Flash (Free Tier)")

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
                    st.error("No search results found for that keyword.")
                    st.stop()
                
                comp_url = search_data['organic'][0]['link'].split('?')[0]
                st.info(f"Targeting Competitor: {comp_url}")

            # STEP 2: Scrape both sites
            with st.spinner("📄 Scraping content..."):
                user_scrape = firecrawl.scrape(user_url, formats=['markdown'])
                comp_scrape = firecrawl.scrape(comp_url, formats=['markdown'])
                
                # Use getattr for safety with the Document object
                u_md = getattr(user_scrape, 'markdown', "")[:8000]
                c_md = getattr(comp_scrape, 'markdown', "")[:8000]

            # STEP 3: AI Analysis (Fixed NameError Sequence)
            if not u_md or not c_md:
                st.error("Could not extract content from one of the sites.")
                st.stop()

            with st.spinner("♊ Gemini 3 is analyzing the gap..."):
                # FIRST: Define the prompt
                analysis_prompt = (
                    f"Perform a professional SEO content gap analysis.\n\n"
                    f"User URL: {user_url}\n"
                    f"Competitor URL: {comp_url}\n"
                    f"Target Keyword: {target_keyword}\n\n"
                    f"USER CONTENT (Markdown):\n{u_md}\n\n"
                    f"COMPETITOR CONTENT (Markdown):\n{c_md}\n\n"
                    "Output a report with 3 specific missing topics and a clear execution plan."
                )
                
                # SECOND: Call the model using the defined prompt
                response = client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=analysis_prompt
                )
                
                if response.text:
                    st.session_state.report_content = response.text
                    st.session_state.report_ready = True
                    st.session_state.current_url = user_url
                    st.session_state.current_keyword = target_keyword
                else:
                    st.error("AI returned an empty response.")

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

# --- 5. DISPLAY & LEAD CAPTURE ---
if st.session_state.report_ready:
    st.divider()
    st.subheader("📊 The Content Gap Report")
    st.markdown(st.session_state.report_content)
    
    st.divider()
    with st.form("lead_capture"):
        st.subheader("📬 Get the Full Strategy PDF")
        email = st.text_input("Email Address")
        submit_lead = st.form_submit_button("Send Me the Report")
        
        if submit_lead:
            if "@" not in email:
                st.error("Invalid email.")
            else:
                webhook_url = "https://hook.us2.make.com/i4ntiyak1rrawyvbfvrbe1y73vgg44ia"
                payload = {
                    payload = {
                        "email": email,
                        "url": st.session_state.current_url,
                        "keyword": st.session_state.current_keyword,
                        "summary": st.session_state.report_content  # <--- MAKE SURE THIS IS HERE
                    }
                    res = requests.post(webhook_url, json=payload)
                }
                requests.post(webhook_url, json=payload)
                st.balloons()
                st.success("Success! Check your inbox.")
