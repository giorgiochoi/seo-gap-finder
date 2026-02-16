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
client = genai.Client(
    api_key=gemini_key, 
    http_options={'api_version': 'v1beta'} 
)

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
with st.spinner("♊ Gemini 3 is analyzing..."):
    # gemini-3-flash-preview is the most powerful free-tier model available today
    try:
        response = client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt
        )
        st.session_state.report_content = response.text
        st.session_state.report_ready = True
    except Exception as e:
        # Fallback to the stable 2.5 if preview is hitting rate limits
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt
        )
        st.session_state.report_content = response.text
        st.session_state.report_ready = True
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
