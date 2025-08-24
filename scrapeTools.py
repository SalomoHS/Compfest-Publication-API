from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
import os
import json
from dotenv import load_dotenv
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",google_api_key=os.getenv("GOOGLE_API_KEY")
)

@tool
async def summarize_news(content:str) -> dict:
    """
    Extract article metadata like title, url, and 
    summarize the article (include city and published date). Output Indonesian only.
    Args:
        content (str): The content of the article.
    Returns:
        dict: A dictionary containing the article title, article url, summarized article content in Indonesian.
    """
    response = await llm.ainvoke(
        f"""
        From the following article, do three tasks:
        1. Summarize the article in Indonesian. The summary must include the city and the published date.
        2. Extract the article title.
        3. Extract the article url.

        Return the result ONLY strictly in JSON format with this structure:
        {{
            "article_summary": "...",
            "article_title": "...",
            "article_url": "...",
        }}

        Article:\n\n{content}
        """
    )
    
    result = json.loads(response.content)
    return {"news_summary": result['article_summary'], 
    "news_title":result['article_title'], "news_urls":result['article_url'],}