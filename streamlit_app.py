import streamlit as st
import requests
import os
from firecrawl import Firecrawl # Modern v2 SDK
from langchain_anthropic import ChatAnthropic

# --- 1. SETUP ---
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍")
st.title("🔍 SEO Content Gap Finder")

anthropic_key = st.secrets.get("ANTHROPIC_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY")
serper_key = st.secrets.get("SERPER_API_KEY")

if not all([anthropic_key, firecrawl_key, serper_key]):
    st.error("Missing API keys in Streamlit Secrets.")
    st.stop()

# Initialize SDK
firecrawl = Firecrawl(api_key=firecrawl_key)
model = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=anthropic_key)

# --- 2. STATE MANAGEMENT ---
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# --- 3. AUDIT FORM ---
with st.sidebar:
    st.header("Project Settings")
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword", placeholder="best wireless headphones")
    submit = st.button("Run Analysis")

if submit:
    with st.spinner("🕵️ Searching and Scraping..."):
        try:
            # Step 1: Search via Serper
            headers = {'X-API-KEY': serper_key, 'Content-Type': 'application/json'}
            search_res = requests.post('https://google.serper.dev/search', json={"q": target_keyword, "num": 1}, headers=headers)
            search_json = search_res.json()
            
            if 'organic' not in search_json or not search_json['organic']:
                st.error("No search results found for that keyword.")
                st.stop()
                
            comp_url = search_json['organic'][0]['link'].split('?')[0]
            st.info(f"Targeting Competitor: **{comp_url}**")

            # Step 2: Scrape using v2 SDK (Dot Notation)
            user_data = firecrawl.scrape(user_url, formats=['markdown'])
            comp_data = firecrawl.scrape(comp_url, formats=['markdown'])
            
            # Use dot notation to access the Document object attributes
            u_md = getattr(user_data, 'markdown', "")[:6000]
            c_md = getattr(comp_data, 'markdown', "")[:6000]
            
            if not u_md or not c_md:
                st.error("Scraper returned empty content. The site may be blocking the request.")
                st.stop()

            # Step 3: AI Analysis
            prompt = (
                f"Compare {user_url} vs {comp_url} for '{target_keyword}'. "
                f"Provide 3 missed sub-topics and a 200-word execution plan.\n\n"
                f"USER CONTENT: {u_md}\n\n"
                f"COMPETITOR CONTENT: {c_md}"
            )
            response = model.invoke(prompt)
            
            st.session_state.report_content = response.content
            st.session_state.report_ready = True
            st.session_state.current_url = user_url
            st.session_state.current_keyword = target_keyword
            
        except Exception as e:
            st.error(f"Error: {e}")

# --- 4. DISPLAY & LEAD CAPTURE ---
if st.session_state.report_ready:
    st.markdown("---")
    st.markdown("### 📊 The Gap Report")
    st.write(st.session_state.report_content)
    
    with st.form("lead_capture"):
        st.subheader("📬 Get the Full 10-Page Strategy")
        email = st.text_input("Email Address")
        if st.form_submit_button("Send Me the Full Report"):
            webhook_url = "https://hook.us2.make.com/i4ntiyak1rrawyvbfvrbe1y73vgg44ia"
            requests.post(webhook_url, json={
                "email": email, 
                "url": st.session_state.current_url, 
                "keyword": st.session_state.current_keyword
            })
            st.balloons()
            st.success("Sent! Check your inbox shortly.")
