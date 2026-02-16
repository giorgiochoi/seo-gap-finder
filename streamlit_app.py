import streamlit as st
import requests
import re
import time
from firecrawl import Firecrawl
from google import genai

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍", layout="wide")

# Fetch keys from Streamlit Secrets
gemini_key = st.secrets.get("GEMINI_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY")
serper_key = st.secrets.get("SERPER_API_KEY")

# MAKE.COM CONFIG
# Replace the string below with your actual Webhook URL from Make.com
WEBHOOK_URL = "https://hook.us2.make.com/i4ntiyak1rrawyvbfvrbe1y73vgg44ia" 

if not all([gemini_key, firecrawl_key, serper_key]):
    st.error("Missing API keys. Please check your Streamlit Secrets.")
    st.stop()

# Initialize SDKs
firecrawl = Firecrawl(api_key=firecrawl_key)
client = genai.Client(api_key=gemini_key, http_options={'api_version': 'v1beta'})

# --- 2. FORMATTING HELPER ---
def markdown_to_safe_html(text):
    """
    Converts markdown to standard, semantic HTML for Email and Google Docs.
    """
    # 1. Headers: ### Title -> <h3>Title</h3>
    text = re.sub(r'### (.*?)\n', r'<h3>\1</h3>', text)
    # 2. Bold: **Text** -> <b>Text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # 3. Lists: * Item -> <li>Item</li>
    text = re.sub(r'\* (.*?)\n', r'<li>\1</li>', text)
    # 4. Newlines: Standard breaks
    text = text.replace('\n', '<br>')
    # 5. Wrap in body for Google Doc rendering
    return f"<html><body>{text}</body></html>"

# --- 3. STATE MANAGEMENT ---
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# --- 4. UI LAYOUT ---
st.title("🔍 AI SEO Content Gap Finder")
st.caption("Identify exactly why your competitors are outranking you.")

with st.sidebar:
    st.header("Project Settings")
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword", placeholder="e.g., luxury smartphones")
    st.divider()
    run_btn = st.button("🚀 Run AI Analysis", use_container_width=True)

# --- 5. CORE ANALYSIS LOGIC ---
if run_btn:
    if not user_url or not target_keyword:
        st.warning("Please provide both your URL and a target keyword.")
    else:
        try:
            # STEP 1: Find Competitor
            with st.spinner("🕵️ Searching for top-ranking competitor..."):
                headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
                search_res = requests.post('https://google.serper.dev/search', 
                                         json={"q": target_keyword, "num": 1}, headers=headers)
                comp_url = search_res.json()['organic'][0]['link'].split('?')[0]
                st.session_state.current_comp = comp_url

            # STEP 2: Scrape Content
            with st.spinner(f"📄 Scraping {user_url} and {comp_url}..."):
                user_scrape = firecrawl.scrape(user_url, formats=['markdown'])
                comp_scrape = firecrawl.scrape(comp_url, formats=['markdown'])
                u_md = getattr(user_scrape, 'markdown', "")[:8000]
                c_md = getattr(comp_scrape, 'markdown', "")[:8000]

            # STEP 3: Gemini Analysis (with 503 Retry)
            with st.spinner("♊ AI is analyzing content gaps..."):
                prompt = f"""
                You are a Senior SEO Specialist. Compare {user_url} vs {comp_url} for '{target_keyword}'.
                Output three sections separated by '---':
                1. Strategic Context
                ---
                2. Three Specific Content Gaps
                ---
                3. A 4-Step Execution Plan to Outrank Them
                """
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(model='gemini-3-flash-preview', contents=prompt)
                        st.session_state.report_content = response.text
                        st.session_state.report_ready = True
                        st.session_state.current_url = user_url
                        st.session_state.current_keyword = target_keyword
                        break 
                    except Exception as e:
                        if "503" in str(e) and attempt < max_retries - 1:
                            time.sleep((attempt + 1) * 2)
                            continue
                        else: raise e

        except Exception as e:
            st.error(f"Analysis failed: {e}")

# --- 6. DISPLAY & LEAD CAPTURE ---
if st.session_state.report_ready:
    st.divider()
    st.subheader(f"📊 Preview Report: {st.session_state.current_url}")
    # Show only the first two sections as a 'tease' on screen
    tease_view = "---".join(st.session_state.report_content.split("---")[:2])
    st.markdown(tease_view)
    
    st.info("💡 The full 4-Step Execution Plan is available via the PDF report below.")

    st.divider()
    with st.form("lead_capture_form", clear_on_submit=True):
        st.subheader("📬 Send Full Blueprint to My Inbox")
        email_input = st.text_input("Email Address")
        submit_lead = st.form_submit_button("Get the Full Strategy (PDF)")
        
        if submit_lead:
            if "@" not in email_input:
                st.error("Invalid email address.")
            else:
                # 1. Tease & Reveal Logic
                parts = st.session_state.report_content.split("---")
                email_body = parts[0] + (parts[1] if len(parts) > 1 else "")
                
                # 2. Prep Payload
                payload = {
                    "email": email_input, 
                    "url": st.session_state.current_url, 
                    "keyword": st.session_state.current_keyword,
                    "email_content": markdown_to_safe_html(email_body),
                    "pdf_content": markdown_to_safe_html(st.session_state.report_content)
                }
                
                try:
                    res = requests.post(WEBHOOK_URL, json=payload)
                    if res.status_code == 200:
                        st.balloons()
                        st.success(f"Success! Teaser sent to {email_input} with a full PDF attached. Check your spam folder—sometimes the AI gets too excited!")
                    else:
                        st.error(f"Make.com Error: {res.status_code}")
                except Exception as e:
                    st.error(f"Connection error: {e}")
