from groundx import Groundx
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

# Setting up API keys
groundx = Groundx(
    api_key=os.environ['GROUNDX_API_KEY']
)

#===============================================================================
# Action Parsing
#===============================================================================

#action determiner
class Action(TypedDict):
    scroll_up: bool
    scroll_down: bool
    next_page: bool
    previous_page: bool
    snap_page: bool
    find_fig: bool
    find_pdf: bool
    non_determ: bool

action_parse_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Decide if the user wants one of the following actions performed:
            - `scroll_up`: scroll up a small amount within one page of the pdf
            - `scroll_down`: scroll down a small amount within one page of the pdf
            - `snap_page`: snap to a specific page of a pdf
            - `find_fig`: find a specific figure, table, image, or specific item.
            - `find_doc`: find a specific doc
            - `non_determ`: no valid action is discernable
            These are mutually exclusive. One should be true, the rest should be false.
            note: you can use snap_page to go to a page relative to the current page.
            note: blanket questions should default to find figure, unless they're obviously about a document
            """,
        ),
        ("placeholder", "{messages}"),
    ]
)

action_parser = action_parse_prompt | ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(Action)

#===============================================================================
# Snap Page Parsing
#===============================================================================

class SnapPage(TypedDict):
    snap_page: int

snap_page_parse_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """Parse out the specific page of the pdf the user wants to snap to.
            """,
        ),
        ("placeholder", "{messages}"),
    ]
)

snap_page_parser = snap_page_parse_prompt | ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(SnapPage)

#===============================================================================
# Figure Description Parsing
#===============================================================================

class FigDesc(TypedDict):
    figure_description: str

fig_desc_parse_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """The user wants to find a figure. Extract a description of the figure the user needs.
            """,
        ),
        ("placeholder", "{messages}"),
    ]
)

fig_desc_parser = fig_desc_parse_prompt | ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(FigDesc)

#===============================================================================
# Document Description Parsing
#===============================================================================

class DocDesc(TypedDict):
    doc_description: str

doc_desc_parse_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """The user wants to find a document. Extract a description of the document the user needs.
            """,
        ),
        ("placeholder", "{messages}"),
    ]
)

doc_desc_parser = doc_desc_parse_prompt | ChatOpenAI(
    model="gpt-4o", temperature=0
).with_structured_output(DocDesc)

#===============================================================================
# Search for Figure
#===============================================================================

bucket_id = 11795

def gx_search_figure(query):

    response = groundx.search.content(
        id=bucket_id,
        query=query
    )

    semantic_object = response.body['search']['results'][0]

    return semantic_object['sourceUrl'], semantic_object['boundingBoxes'][0]['pageNumber']

#===============================================================================
# Search for Documents
#===============================================================================

def gx_search_document(query):

    response = groundx.search.content(
        id=bucket_id,
        query=query
    )

    semantic_object = response.body['search']['results'][0]

    return semantic_object['sourceUrl']

#===============================================================================
# Old Endpoint
#===============================================================================

def handle_query(query, context):
    #getting action that should be performed
    response = action_parser.invoke({"messages": [("ai", "my name is doc tech, what action would you like me to perform?"),("user", query)]})
    response['pdf']= None
    response['page']=None

    #doing follow up as necessary
    if response['snap_page']:
        response['page']=snap_page_parser.invoke({"messages": [("ai", f"my name is doc tech, what page would you like to snap to. Current state: {context}"),("user", query)]})
    elif response['find_fig']:
        response['pdf'], response['page'] = gx_search_figure(query)
    elif response['find_pdf']:
        response['pdf'] = gx_search_document(query)

    return response

#===============================================================================
# New Endpoints With Voice
#===============================================================================

def decide_and_respond(query, context):
    #getting action that should be performed
    response = action_parser.invoke({"messages": [("ai", "my name is doc tech, what action would you like me to perform?"),("user", query)]})
    response['query']= query
    response['context']=context
    response['page']=None

    #doing follow up as necessary
    if response['snap_page']:
        response['page']=snap_page_parser.invoke({"messages": [("ai", f"my name is doc tech, what page would you like to snap to. Current state: {context}"),("user", query)]})

    #Prompting the language model to come up with a response.
    class VerbalResponse(TypedDict):
        response: str

    verb_resp_parse_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"""You will be given a users query, and the actions a system decided to take based on that query.
                respond to the user verbally, informing them what action will be taken. Be breif.
                """,
            ),
            ("placeholder", "{messages}"),
        ]
    )

    verb_resp_parser = verb_resp_parse_prompt | ChatOpenAI(
        model="gpt-4o", temperature=0
    ).with_structured_output(VerbalResponse)

    verbal_response = verb_resp_parser.invoke({"messages": [("user", query),("ai", str(response))]})['response']
    print('verbal response:')
    print(verbal_response)

    #constructing audio
    from openai import OpenAI
    client = OpenAI()

    speech_file_path = "speech.mp3"
    r = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input=verbal_response
    )
    r.stream_to_file(speech_file_path)

    #returning json object
    return response

def handle_action(response):
    query = response['query']
    context = response['context']
    response['pdf']= None
    response['page']=None

    #doing follow up as necessary
    if response['find_fig']:
        response['pdf'], response['page'] = gx_search_figure(query)
    elif response['find_pdf']:
        response['pdf'] = gx_search_document(query)

    return response