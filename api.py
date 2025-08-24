from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from firecrawl import FirecrawlApp
from pydantic import BaseModel
from typing import List
from .flow import run_ai_agent
import os
from dotenv import load_dotenv
load_dotenv()


mcp = FastMCP("detik")
firecrawl = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API"))

class ScrapeResultSchema(BaseModel):
    url: str

class PodcastRequest(BaseModel):
    location: str
    language: str
    duration: str
    style: str
    format: str
    speakers: List[str]

@mcp.tool
async def greet(name):
    return f"Hello world {name}"

@mcp.tool()
async def crawl_detik_com(location: str) -> dict:
    """
    Get the latest news from detik.news about urban living based on given location.
    Args:
        location (str): The location to search for news.
    Returns:
        dict: A dictionary containing the latest news URL about urban living for the given location.
    """
    print("CRAWL:",location)
    crawl = firecrawl.extract(
            [f'https://www.detik.com/search/searchall?query={location}'],
            prompt='Extract 1 the most recent news url about urban living.',
            schema=ScrapeResultSchema.model_json_schema()
        )
    print("CRAWLL:",crawl)
    return {
        "latest_news_url": crawl.data['url'],
    }

@mcp.tool()
async def scrape_news(url:str) -> dict:
    """
    Scrape the latest news and return markdown.
    Args:
        url (str): The URL of the latest news to scrape.
    Returns:
        dict: A dictionary containing the scraped latest news content in markdown format.
    """
    print("SCRAPE:",url)

    scrape = firecrawl.scrape_url(url, formats=['markdown'])
    print("SCRAPEE:",scrape)
    return {'news_content':scrape.markdown}

mcp_app = mcp.http_app(path='/')

app = FastAPI(lifespan=mcp_app.lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/mcp", mcp_app)

@app.get("/")
async def root():
    return {"message": "API is running"}

@app.post("/publish_podcast")
async def publish_podcast(request: PodcastRequest):
    try:
        res = await run_ai_agent(
            language=request.language,
            duration=request.duration,
            style=request.style,
            format=request.format,
            speakers=request.speakers,
            location=request.location
        )

        return {"Success", res}
    except Exception as e:
        return {"Failed": e}
