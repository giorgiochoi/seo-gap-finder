import streamlit as st
from firecrawl import FirecrawlApp
from langchain_anthropic import ChatAnthropic
import os

# 1. Setup Page Config
st.set_page_config(page_title="AI SEO Gap Finder", page_icon="🔍")
st.title("🔍 SEO Content Gap Finder")
st.write("Enter your URL and a keyword to find exactly what your competitors are doing better.")

# 2. Get API Keys (From Streamlit Secrets or Local .env)
# When deployed, it looks in "Secrets". Locally, it looks for environment variables.
anthropic_key = st.secrets.get("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
firecrawl_key = st.secrets.get("FIRECRAWL_API_KEY") or os.getenv("FIRECRAWL_API_KEY")

if not anthropic_key or not firecrawl_key:
    st.error("API Keys missing! Please add them to your Streamlit Secrets.")
    st.stop()

# 3. Initialize Engines
firecrawl = FirecrawlApp(api_key=firecrawl_key)
model = ChatAnthropic(model="claude-3-5-sonnet-20240620", api_key=anthropic_key)

# 4. The UI Form
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
                search_results = firecrawl.search(target_keyword, params={'limit': 1})
                comp_url = search_results[0]['url']
                
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
                
                st.success("Analysis Complete!")
                st.markdown("### 📊 The Gap Report")
                st.write(response.content)
                
            except Exception as e:
                st.error(f"An error occurred: {e}")
