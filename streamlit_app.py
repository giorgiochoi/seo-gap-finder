import streamlit as st
import requests
from firecrawl import Firecrawl
from google import genai 

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍", layout="wide")

gemini_key = st.secrets.get("GEMINI_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY")
serper_key = st.secrets.get("SERPER_API_KEY")

if not all([gemini_key, firecrawl_key, serper_key]):
    st.error("Missing API keys in Secrets.")
    st.stop()

# Initialize SDKs with API version fix
firecrawl = Firecrawl(api_key=firecrawl_key)
client = genai.Client(api_key=gemini_key, http_options={'api_version': 'v1'})

if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# --- 3. UI ---
st.title("🔍 SEO Content Gap Finder")
with st.sidebar:
    st.header("Project Settings")
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword")
    run_btn = st.button("Run Analysis", use_container_width=True)

# --- 4. CORE LOGIC ---
if run_btn:
    if not user_url or not target_keyword:
        st.warning("Please provide both a URL and a keyword.")
    else:
        try:
            # STEP 1: Search
            headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
            search_res = requests.post('https://google.serper.dev/search', json={"q": target_keyword, "num": 1}, headers=headers)
            comp_url = search_res.json()['organic'][0]['link'].split('?')[0]
            st.info(f"Targeting Competitor: {comp_url}")

            # STEP 2: Scrape
            with st.spinner("📄 Scraping sites..."):
                user_data = firecrawl.scrape(user_url, formats=['markdown'])
                comp_data = firecrawl.scrape(comp_url, formats=['markdown'])
                u_md = getattr(user_data, 'markdown', "")[:8000]
                c_md = getattr(comp_data, 'markdown', "")[:8000]

            # STEP 3: Gemini Analysis
            with st.spinner("♊ Gemini is analyzing..."):
                prompt = f"Compare {user_url} vs {comp_url} for '{target_keyword}'. Provide 3 missed topics and a 200-word plan.\n\nUSER: {u_md}\n\nCOMP: {c_md}"
                response = client.models.generate_content(model='gemini-1.5-flash-latest', contents=prompt)
                
                st.session_state.report_content = response.text
                st.session_state.report_ready = True
                st.session_state.current_url = user_url
                st.session_state.current_keyword = target_keyword
        except Exception as e:
            st.error(f"Error: {e}")

# --- 5. DISPLAY ---
if st.session_state.report_ready:
    st.divider()
    st.markdown(st.session_state.report_content)
    with st.form("lead_capture"):
        email = st.text_input("Email Address")
        if st.form_submit_button("Send Me the Full Report"):
            requests.post("https://hook.us2.make.com/i4ntiyak1rrawyvbfvrbe1y73vgg44ia", 
                          json={"email": email, "url": st.session_state.current_url, "keyword": st.session_state.current_keyword})
            st.success("Sent!")
