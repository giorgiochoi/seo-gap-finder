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
    st.error("Missing API keys in Streamlit Secrets. Please check your .streamlit/secrets.toml or Streamlit Cloud settings.")
    st.stop()

# Initialize SDKs
# Note: Ensure you have firecrawl-py and google-genai installed
firecrawl = Firecrawl(api_key=firecrawl_key)
client = genai.Client(api_key=gemini_key, http_options={'api_version': 'v1beta'})

# --- 2. FORMATTING HELPER ---
def markdown_to_safe_html(text):
    """
    Converts markdown to standard HTML tags that Google Docs 
    and Email clients both understand easily.
    """
    # 1. Handle Headers (### Header) -> <h3>Header</h3>
    text = re.sub(r'### (.*?)\n', r'<h3>\1</h3>', text)
    # 2. Handle Bold (**Text**) -> <b>Text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # 3. Handle Lists (* Item) -> <li>Item</li>
    # We wrap them in <ul> for proper bullet formatting
    text = re.sub(r'\* (.*?)\n', r'<ul><li>\1</li></ul>', text)
    # 4. Convert newlines to standard paragraph breaks
    text = text.replace('\n', '<p></p>')
    
    return text

# --- 3. STATE MANAGEMENT ---
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# --- 4. UI LAYOUT ---
st.title("🔍 AI SEO Content Gap Finder")
st.caption("Compare your site against top-ranking competitors in seconds.")

with st.sidebar:
    st.header("Project Settings")
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword", placeholder="luxury watches")
    
    st.divider()
    run_btn = st.button("🚀 Run AI Analysis", use_container_width=True)

# --- 5. CORE ANALYSIS LOGIC ---
if run_btn:
    if not user_url or not target_keyword:
        st.warning("Please provide both your URL and a target keyword.")
    else:
        try:
            # STEP 1: Find Competitor via Serper.dev
            with st.spinner("🕵️ Finding the top-ranking competitor..."):
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
                st.session_state.current_comp = comp_url

            # STEP 2: Scrape Content via Firecrawl
            with st.spinner(f"📄 Scraping {user_url} and {comp_url}..."):
                # Using the latest .scrape() syntax
                user_scrape = firecrawl.scrape(user_url, formats=['markdown'])
                comp_scrape = firecrawl.scrape(comp_url, formats=['markdown'])
                
                u_md = getattr(user_scrape, 'markdown', "")[:8000]
                c_md = getattr(comp_scrape, 'markdown', "")[:8000]

            # STEP 3: Generate Analysis via Gemini (with Retry Logic)
            with st.spinner("♊ AI is analyzing content gaps..."):
                prompt = f"""
                You are a Senior SEO Specialist. Compare the following two websites for the keyword: '{target_keyword}'.
                
                Our Site Content: {u_md}
                Competitor Site Content: {c_md}
                
                Provide:
                1. A brief strategic context.
                2. Three specific content gaps the competitor covers that we don't.
                3. A 4-step execution plan to outrank them.
                
                Use Markdown formatting. Be specific and technical.
                """
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = client.models.generate_content(
                            model='gemini-3-flash-preview', 
                            contents=prompt
                        )
                        st.session_state.report_content = response.text
                        st.session_state.report_ready = True
                        st.session_state.current_url = user_url
                        st.session_state.current_keyword = target_keyword
                        break 
                    except Exception as gemini_err:
                        if "503" in str(gemini_err) and attempt < max_retries - 1:
                            time.sleep((attempt + 1) * 2)
                            continue
                        else:
                            raise gemini_err

        except Exception as e:
            st.error(f"Analysis failed: {e}")

# --- 6. DISPLAY & LEAD CAPTURE ---
if st.session_state.report_ready:
    st.divider()
    st.subheader(f"📊 Content Gap Report: {st.session_state.current_url}")
    st.markdown(st.session_state.report_content)
    
    st.divider()
    # The Lead Capture Form
    with st.form("lead_capture_form", clear_on_submit=True):
        st.subheader("📬 Email This Report as a PDF")
        email_input = st.text_input("Enter your email address")
        submit_lead = st.form_submit_button("Send Full PDF Strategy")
        
        if submit_lead:
            if "@" not in email_input or "." not in email_input:
                st.error("Please enter a valid email address.")
            else:
                # Format the report into safe HTML for the Webhook
                html_report = markdown_to_safe_html(st.session_state.report_content)
                
                payload = {
                    "email": email_input, 
                    "url": st.session_state.current_url, 
                    "keyword": st.session_state.current_keyword,
                    "summary": html_report 
                }
                
                try:
                    # Final safety check on URL
                    if not WEBHOOK_URL.startswith("http"):
                        st.error("Invalid Webhook URL. Please check your script configuration.")
                    else:
                        response = requests.post(WEBHOOK_URL, json=payload)
                        if response.status_code == 200:
                            st.balloons()
                            st.success(f"Success! The PDF is being generated and sent to {email_input}")
                        else:
                            st.error(f"Delivery Service Error (Make.com): {response.status_code}")
                except Exception as e:
                    st.error(f"Could not connect to Delivery Service: {e}")
