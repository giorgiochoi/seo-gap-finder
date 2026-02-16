import streamlit as st
import requests
import os
from firecrawl import Firecrawl 
from langchain_anthropic import ChatAnthropic

# 1. Setup Page Config
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍")
st.title("🔍 SEO Content Gap Finder")
st.write("Enter your URL and a keyword to find exactly what your competitors are doing better.")

# 2. GET KEYS FIRST (Corrected Order)
anthropic_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY") or os.getenv("FIRECRAWL_API_KEY")

# 3. DEBUGGING & VALIDATION
if firecrawl_key:
    st.info(f"Firecrawl Key detected: {firecrawl_key[:5]}...") 
else:
    st.error("Firecrawl Key NOT found in secrets!")
    st.stop()

if not anthropic_key:
    st.error("Anthropic Key NOT found in secrets!")
    st.stop()

# 4. INITIALIZE ENGINES
# We do this once, correctly, using the modern 'Firecrawl' class
try:
    firecrawl = Firecrawl(api_key=firecrawl_key)
    model = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=anthropic_key)
except Exception as e:
    st.error(f"Failed to initialize engines: {e}")
    st.stop()

# 5. SESSION STATE
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "report_content" not in st.session_state:
    st.session_state.report_content = ""

# 6. THE MAIN AUDIT FORM
with st.form("audit_form"):
    user_url = st.text_input("Your Website URL", placeholder="https://mywebsite.com")
    target_keyword = st.text_input("Target Keyword", placeholder="best wireless headphones")
    submit = st.form_submit_button("Run Analysis")

if submit:
    if not user_url or not target_keyword:
        st.warning("Please fill in both fields.")
    else:
        with st.spinner("🕵️ Agent is crawling the web..."):
            try:
                # Step 1: Search for the top competitor
                search_results = firecrawl.search(target_keyword, limit=1)
                
                # Check if 'data' exists in the results object
                if search_results and hasattr(search_results, 'data') and len(search_results.data) > 0:
                    comp_url = search_results.data[0]['url']
                elif isinstance(search_results, list) and len(search_results) > 0:
                    # Fallback for older versions that return a list
                    comp_url = search_results[0]['url']
                else:
                    st.error("No search results found for that keyword.")
                    st.stop()
                
                # Step 2: Scrape both sites
                st.write(f"Analyzing your site vs. **{comp_url}**")
                user_scrape = firecrawl.scrape_url(user_url, params={'formats': ['markdown']})
                comp_scrape = firecrawl.scrape_url(comp_url, params={'formats': ['markdown']})
                
                # Step 3: AI Analysis
                prompt = f"""
                Act as a Senior SEO Strategist. 
                Compare the user's content (below) with the top-ranking competitor for '{target_keyword}'.
                
                USER CONTENT: {user_scrape['markdown'][:6000]}
                COMPETITOR CONTENT: {comp_scrape['markdown'][:6000]}
                
                Provide:
                1. THREE specific sub-topics the competitor covers that the user missed.
                2. A brief 200-word 'Execution Plan' to outrank them.
                """
                
                response = model.invoke(prompt)
                
                # Save to session state
                st.session_state.report_content = response.content
                st.session_state.report_ready = True
                st.session_state.current_url = user_url
                st.session_state.current_keyword = target_keyword
                
            except Exception as e:
                st.error(f"An error occurred during analysis: {e}")

# 7. DISPLAY REPORT AND LEAD CAPTURE
if st.session_state.report_ready:
    st.success("Analysis Complete!")
    st.markdown("### 📊 The Gap Report")
    st.write(st.session_state.report_content)
    
    st.markdown("---")
    st.subheader("📬 Want the Full 10-Page Content Blueprint?")
    st.write("Enter your email to receive the complete step-by-step execution plan.")
    
    with st.form("lead_capture"):
        email = st.text_input("Email Address")
        lead_submit = st.form_submit_button("Send Me the Full Report")
        
        if lead_submit:
            if "@" in email and "." in email:
                webhook_url = "https://hook.us2.make.com/i4ntiyak1rrawyvbfvrbe1y73vgg44ia"
                payload = {
                    "email": email,
                    "url": st.session_state.current_url,
                    "keyword": st.session_state.current_keyword,
                    "summary": st.session_state.report_content[:1000]
                }
                
                try:
                    res = requests.post(webhook_url, json=payload)
                    if res.status_code == 200:
                        st.balloons()
                        st.success("Success! Your report is on the way.")
                    else:
                        st.error("Webhook error. Please try again.")
                except Exception as e:
                    st.error(f"Failed to send lead: {e}")
            else:
                st.error("Please enter a valid email address.")
