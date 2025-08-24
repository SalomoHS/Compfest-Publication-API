from .agent import agent, tools, scrape_agent
from .tools import *
from langchain_core.messages import HumanMessage
from langgraph.graph import START, StateGraph, END
from langgraph.prebuilt import ToolNode
from .extendMessages import ExtendedMessagesState
import pprint
pp = pprint.PrettyPrinter(indent=2, width=100)


def should_continue(state):
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "tools"
    else:
        return "json_parser"

def should_continue_scrape(state):
    last_message = state['messages'][-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    pp.pprint(f"LAST MESSSAGE==: {last_message}")
    if tool_calls is None and isinstance(last_message, dict):
        tool_calls = last_message.get("tool_calls", [])

    pp.pprint(f"Tool calls: {tool_calls}")
    
    if tool_calls and len(tool_calls) > 0:
        pp.pprint("Routing to scrape_tools")
        return "scrape_tools"

    return "json_parser"


async def run_ai_agent( language: str, location,
            duration: str, style: str,
            format: str,
            speakers: str
):

    scrape_tools = await get_scrape_tools() 
    builder = StateGraph(ExtendedMessagesState) 
    
    builder.add_node("scrape_agent",scrape_agent)
    builder.add_node("agent",agent)

    builder.add_node("tools",ToolNode(tools))
    builder.add_node("scrape_tools",ToolNode(scrape_tools))

    builder.add_node("json_parser", json_parser)
    builder.add_node("update_news_metadata", update_state_news_metadata)
    builder.add_node("generate_dialog", generate_dialog)
    builder.add_node("insert_podcast", insert_podcast)
    builder.add_node("insert_conversation", insert_conversation)
    builder.add_node("make_audio_hooks", make_audio_hooks)
    builder.add_node("create_video", create_video)
    builder.add_node("upload_to_tiktok", upload_to_tiktok)

    builder.add_edge(START,"scrape_agent")
    builder.add_conditional_edges("scrape_agent",should_continue_scrape)
    builder.add_edge("scrape_tools","scrape_agent")

    builder.add_edge("json_parser","update_news_metadata")
    builder.add_edge("update_news_metadata","agent")

    builder.add_conditional_edges("agent",should_continue)
    builder.add_edge("tools","agent")

    builder.add_edge("json_parser","generate_dialog")
    builder.add_edge("generate_dialog","insert_podcast")
    builder.add_edge("insert_podcast","insert_conversation")
    builder.add_edge("insert_conversation","make_audio_hooks")
    builder.add_edge("make_audio_hooks","create_video")
    builder.add_edge("make_audio_hooks","upload_to_tiktok")
    
    builder.add_edge("upload_to_tiktok",END)
    graph = builder.compile()

    messages = [HumanMessage(content=location)]
    messages = await graph.ainvoke({
        "language":language,
        "duration":duration, "style":style, "format":format,
        "speakers":speakers,
        "messages":messages,
        "location":"surabaya"
        },config={"recursion_limit": 50}
    )

    return messages
