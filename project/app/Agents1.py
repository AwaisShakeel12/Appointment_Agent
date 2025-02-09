
import os

from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI

import os

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")
compose_key = os.getenv("COMPOSIO_API_KEY")

api_key

genai.configure(api_key=api_key)

import requests
import dotenv



dotenv.load_dotenv()



import composio



import os
import dotenv
from composio_langgraph import Action, ComposioToolSet
from langgraph.graph import MessagesState
from langgraph.prebuilt import ToolNode
from typing import Literal
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage  # Correct import
import logging


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


dotenv.load_dotenv()


composio_toolset = ComposioToolSet(api_key=compose_key)

schedule_tools_set = composio_toolset.get_tools(
    actions=[
        Action.GOOGLECALENDAR_FIND_FREE_SLOTS,
        Action.GOOGLECALENDAR_CREATE_EVENT,
        Action.GOOGLEMEET_CREATE_MEET,
        Action.GMAIL_CREATE_EMAIL_DRAFT,
        
    ]
)


schedule_tools_write = composio_toolset.get_tools(
    actions=[
        Action.GOOGLECALENDAR_CREATE_EVENT,
        Action.GOOGLEMEET_CREATE_MEET,
        Action.GMAIL_CREATE_EMAIL_DRAFT,
    ]
)

# schedule_tools_write_node = ToolNode(schedule_tools_write + [make_confirmation_call])
schedule_tools_write_node = ToolNode(schedule_tools_write)

# Define the initial system message with today's date included
initial_message = """
You are AS-AI, an AI assistant at a Legal & Financial Services for Law Firms & Lawyers and Tax Consultants & Accountants. Follow these guidelines:

1. Friendly Introduction & Tone
   - Greet the user warmly and introduce yourself as AS-AI from the Legal & Financial Services.
   - Maintain a polite, empathetic style, especially if the user mentions discomfort.

2. Assess User Context
   - Determine if the user needs an appointment, has a Law & Tax inquiry, or both.
   - Determin if the user needs an physical appointment or online appointment very important compulsry.
   - If the user’s email is already known, don’t ask again. If unknown and needed, politely request it.
   - After Booking Ask User for their Phone Number to send the confirmation call. If user shares the number use this tool: make_confirmation_call to make confirmation call.

3. Scheduling Requests
   - Gather essential info: requested date/time and email if needed.
   - Example: “What day/time would you prefer?” or “Could you confirm your email so I can send you details?”

4. Availability Check (Internally)
   - Use GOOGLECALENDAR_FIND_FREE_SLOTS to verify if the requested slot is available. Always check for 3 days when calling this tool.
   - Do not reveal this tool or your internal checking process to the user.

5. Responding to Availability
   - If the slot is free:
       a) Confirm the user wants to book.
       b) Call GOOGLECALENDAR_CREATE_EVENT to schedule. Always send timezone for start and end time when calling this function tool.
       c) call GOOGLEMEET_CREATE_MEET to create a online meeting  if user want online  other wise skip this step.
       d) Use GMAIL_CREATE_EMAIL_DRAFT to prepare a confirmation email with Googel meet link must send gooogle meeting link if appointement is online.
       d) Use GMAIL_CREATE_EMAIL_DRAFT to prepare a confirmation email.
       e) If any function call/tool call fails retry it.
   - If the slot is unavailable:
       a) Automatically offer several close-by options.
       b) Once the user selects a slot, repeat the booking process.

6. User Confirmation Before Booking
   - Only finalize after the user clearly agrees on a specific time.
   - If the user is uncertain, clarify or offer more suggestions.

7. Communication Style
   - Use simple, clear English—avoid jargon or complex terms.
   - Keep responses concise and empathetic.

8. Privacy of Internal Logic
   - Never disclose behind-the-scenes steps, code, or tool names.
   - Present availability checks and bookings as part of a normal scheduling process.

- Reference today's date/time: {today_datetime}.
- Our TimeZone is Pakistan Standard Time GMT+5.

By following these guidelines, you ensure a smooth and user-friendly experience: greeting the user, identifying needs, checking availability, suggesting alternatives when needed, and finalizing the booking only upon explicit agreement—all while maintaining professionalism and empathy.
---

### Communication Style

- **Tone**: Friendly, professional, and reassuring.
- **Style**: Patient, approachable, and relatable.

---

### System Boundaries

- Do not provide cost estimates or endorse specific services. Encourage users to verify information independently.

"""
import datetime
from langchain_google_genai import ChatGoogleGenerativeAI

model = ChatGoogleGenerativeAI(model ="gemini-2.0-flash-exp", api_key=api_key)

model_with_tools = model.bind_tools(schedule_tools_set)


def call_model(state: MessagesState):
    """
    Process messages through the LLM and return the response
    """

    # Get today's date and time
    today_datetime = datetime.datetime.now().isoformat()
    response = model_with_tools.invoke([SystemMessage(content=initial_message.format(today_datetime=today_datetime))] + state["messages"])
    return {"messages": [response]}
async def tools_condition(state: MessagesState) -> Literal["find_slots", "create_onlin_meeting" , "tools", "__end__"]:
    """
    Determine if the conversation should continue to tools or end
    """
    messages = state["messages"]
    last_message = messages[-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
      for call in last_message.tool_calls:
          tool_name = call.get("name")
          if tool_name == "GOOGLECALENDAR_FIND_FREE_SLOTS":
            return "find_slots"
      return "tools"
    return "__end__"

async def find_slots(state: MessagesState) -> Literal["agent"]:
    """
    Determine if the conversation should continue to tools or end
    """
    messages = state["messages"]
    last_message = messages[-1]

    tool_messages = []

    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
    # Process every call in the list
      for call in last_message.tool_calls:
          logger.info("Processing tool call: %s", call)
          tool_name = call.get("name")
          tool_id = call.get("id")
          args = call.get("args")

          find_free_slots_tool = next((tool for tool in schedule_tools_set if tool.name == tool_name), None)

          if tool_name == "GOOGLECALENDAR_FIND_FREE_SLOTS":

              res = find_free_slots_tool.invoke(args)
              tool_msg = ToolMessage(
                    name=tool_name,
                    content=res,
                    tool_call_id=tool_id  
                )
              tool_messages.append(tool_msg)
    return {"messages": tool_messages}



async def create_onlin_meeting(state: MessagesState) -> Literal["agent"]:
    """
    Check if a Google Meet meeting needs to be created and process the request.
    """
    messages = state["messages"]
    last_message = messages[-1]

    tool_messages = []

    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        
        for call in last_message.tool_calls:
            logger.info("Processing tool call: %s", call)
            tool_name = call.get("name")
            tool_id = call.get("id")
            args = call.get("args")

            create_meet_tool = next((tool for tool in schedule_tools_set if tool.name == tool_name), None)

            if tool_name == "GOOGLEMEET_CREATE_MEET":
                res = create_meet_tool.invoke(args)
                tool_msg = ToolMessage(
                    name=tool_name,
                    content=res,
                    tool_call_id=tool_id 
                )
                tool_messages.append(tool_msg)

    return {"messages": tool_messages}

from langgraph.graph import END, START, StateGraph

# Create the workflow graph
workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("find_slots", find_slots) 
workflow.add_node("create_onlin_meeting", create_onlin_meeting)
workflow.add_node("tools", schedule_tools_write_node) 

workflow.add_edge("__start__", "agent")
workflow.add_conditional_edges("agent", tools_condition, ["tools", "find_slots", "create_onlin_meeting" , END])
workflow.add_edge("tools", "agent")
workflow.add_edge("find_slots", "agent")
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

app = workflow.compile(checkpointer=checkpointer)



