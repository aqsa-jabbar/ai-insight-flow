"""
agent.py
--------
Builds our AI agent: an LLM (Groq's Llama 3.3) wired up with the two
@tool-decorated functions from tools.py, using LangGraph's create_react_agent.

"""

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

import config
from tools import search_web, scrape_website


SYSTEM_PROMPT = """You are a research analyst AI. When given a website/platform name or URL:
1. If the user gave a direct URL, use scrape_website on it right away.
2. If the user gave a NAME (not a URL), first use search_web to find the official
   site/relevant pages, then use scrape_website on the most relevant result.
3. Optionally use search_web again to gather extra context (competitors, reviews,
   reputation) that wouldn't be on the site itself.
4. Produce a clear structured report with sections: Overview, Key Features,
   Documentation Summary, Use Cases, Pros/Cons.

Only answer questions strictly related to the given link/topic. Do not bring in
unrelated context. If scraping fails, rely on search_web results instead and
mention that the site could not be scraped directly."""


def build_agent():
    """
    Creates a fresh agent instance. We intentionally rebuild this on every
    request (see app.py) rather than caching one global instance, to keep
    behavior predictable and avoid any shared state leaking between users
    on a deployed app.
    """
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        groq_api_key=config.GROQ_API_KEY,
        temperature=0.3,
    )

    tools = [search_web, scrape_website]

    # create_react_agent builds a LangGraph graph, not the older AgentExecutor.
    # It expects/returns messages in the shape: {"messages": [...]}
    agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
    return agent


def run_agent(user_input: str) -> str:
    """
    Convenience wrapper: takes a plain string, runs the agent, and returns
    just the final text answer (so app.py doesn't need to know about the
    internal message-list format).
    """
    agent = build_agent()
    result = agent.invoke({"messages": [("user", user_input)]})
    return result["messages"][-1].content