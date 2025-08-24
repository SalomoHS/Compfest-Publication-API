from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from .tools import get_speakers, get_topics, get_scrape_tools
import os
from dotenv import load_dotenv
load_dotenv()

base_dir = os.path.dirname(__file__)
prompt_path = os.path.join(base_dir, "prompt.txt")
scrape_prompt_path = os.path.join(base_dir, "scrapePrompt.txt")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",google_api_key=os.getenv("GOOGLE_API_KEY")
)
tools = [get_speakers, get_topics]

async def agent(state):
    with open(prompt_path,"r") as f:
        system_prompt = f.read()
    system_prompt = PromptTemplate.from_template(system_prompt)
    system_prompt = system_prompt.format(
        topic=state['news_summary'],
        duration=state["duration"],
        speaker1=state["speakers"][0],
        speaker2=state["speakers"][1],
        language=state["language"],
        format=state["format"],
        style=state["style"]
    )
    llm_with_tools = llm.bind_tools(tools)
    return {
        "messages": await llm_with_tools.ainvoke([SystemMessage(content=system_prompt)] + state['messages'])

    }

async def scrape_agent(state):
    with open(scrape_prompt_path,"r") as f:
        system_prompt = f.read()

    system_prompt = PromptTemplate.from_template(system_prompt)
    system_prompt = system_prompt.format(location = state['location'])
    scrape_tools = await get_scrape_tools()
    llm_with_tools = llm.bind_tools(scrape_tools)

    return {
        "messages": await llm_with_tools.ainvoke([SystemMessage(content=system_prompt)] + state['messages'])
    }