import streamlit as st
import requests
from firecrawl import Firecrawl
from google import genai # Latest 2026 Google SDK
from google.genai import types

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍", layout="wide")

# Fetch keys from Streamlit Secrets
# Make sure to add GEMINI_API_KEY to your Secrets!
gemini_key = st.secrets.get("GEMINI_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY")
serper_key = st.secrets.get("SERPER_API_KEY")

if not all([gemini_key, firecrawl_key, serper_key]):
    st.error("Missing API keys in Secrets. Need: GEMINI_API_KEY, FIRECRAWL_API_KEY, SERPER_API_KEY")
    st.stop()

# Initialize SDKs
firecrawl = Firecrawl(api_key=firecrawl_key)
# Initialize Gemini Client (v2.0 SDK style)
client = genai.Client(api_key=gemini_key)

# --- 2. STATE MANAGEMENT ---
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# --- 3. UI LAYOUT ---
st.title("🔍 SEO Content Gap Finder (Gemini Powered)")
st.markdown("Find gaps between your content and the #1 competitor for free.")

with st.sidebar:
    st.header("Project Settings")
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword", placeholder="best wireless headphones")
    run_btn = st.button("Run Analysis", use_container_width=True)

# --- 4. CORE LOGIC ---
if run_btn:
    if not user_url or not target_keyword:
        st.warning("Please provide both a URL and a keyword.")
    else:
        with st.spinner("🕵️ Finding competitor..."):
            try:
                # STEP 1: Serper.dev Search
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
                st.info(f"Targeting Competitor: {comp_url}")

                # STEP 2: Scrape (Firecrawl v2.0 Dot Notation)
                with st.spinner("📄 Scraping content..."):
                    user_data = firecrawl.scrape(user_url, formats=['markdown'])
                    comp_data = firecrawl.scrape(comp_url, formats=['markdown'])
                    
                    u_md = getattr(user_data, 'markdown', "")[:8000]
                    c_md = getattr(comp_data, 'markdown', "")[:8000]

                # STEP 3: Gemini Analysis (Replaces Claude)
                if not u_md or not c_md:
                    st.error("Scraper returned empty content.")
                    st.stop()

                with st.spinner("♊ Gemini is analyzing..."):
                    prompt = (
                        f"Compare {user_url} vs {comp_url} for '{target_keyword}'.\n\n"
                        f"YOUR CONTENT: {u_md}\n\n"
                        f"COMPETITOR CONTENT: {c_md}\n\n"
                        "Provide a Content Gap Report: 3 missed topics and a 200-word execution plan."
                    )
                    
                    # Modern Gemini Generation Call
                    response = client.models.generate_content(
                        model='gemini-1.5-flash',
                        contents=prompt
                    )
                    
                    st.session_state.report_content = response.text
                    st.session_state.report_ready = True
                    st.session_state.current_url = user_url
                    st.session_state.current_keyword = target_keyword
                    
            except Exception as e:
                st.error(f"Error: {e}")

# --- 5. DISPLAY & LEAD CAPTURE ---
if st.session_state.report_ready:
    st.divider()
    st.subheader("📊 The Gap Report")
    st.markdown(st.session_state.report_content)
    
    with st.form("lead_capture"):
        st.subheader("📬 Get the Full 10-Page Strategy")
        email = st.text_input("Email Address")
        if st.form_submit_button("Send Me the Full Report"):
            webhook_payload = {
                "email": email, 
                "url": st.session_state.current_url, 
                "keyword": st.session_state.current_keyword
            }
            requests.post("https://hook.us2.make.com/i4ntiyak1rrawyvbfvrbe1y73vgg44ia", json=webhook_payload)
            st.balloons()
            st.success("Strategy sent to your inbox!")
