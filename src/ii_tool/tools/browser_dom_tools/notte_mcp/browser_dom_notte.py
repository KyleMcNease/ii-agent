import os
import pathlib
from typing import Annotated, Final, Literal
from dotenv import load_dotenv
from loguru import logger
from fastmcp import FastMCP
from notte_core.actions import ActionUnion, ClickAction, FillAction, CheckAction, PressKeyAction, WaitAction, ScrollUpAction, ScrollDownAction
from notte_core.browser.observation import ExecutionResult, TrajectoryProgress
from notte_core.utils.pydantic_schema import JsonResponseFormat, convert_response_format_to_pydantic_model
from notte_browser.session import NotteSession
from notte_browser.rendering.pipe import DomNodeRenderingPipe, DomNodeRenderingType
from pydantic import BaseModel
import base64
from notte_core.utils.image import image_from_bytes
# #########################################################
# ####################### CONFIG ##########################
# #########################################################

_ = load_dotenv()

mcp_server_path = pathlib.Path(__file__).absolute()
session: NotteSession | None = None
current_step: int = 0

os.environ["NOTTE_MCP_SERVER_PATH"] = str(mcp_server_path)



# Create an MCP server (local browser tools only)
mcp = FastMCP(
    name="Notte MCP Browser Server - Session Management and Web Interactions Only",
)
# #########################################################
# ######################## Models #########################
# #########################################################

class ObservationToolResponse(BaseModel):
    observation: str
    code: str

class ExecutionToolResponse(BaseModel):
    result: ExecutionResult
    code: str

class SessionInfo(BaseModel):
    session_id: str
    status: str
    url: str | None = None

# #########################################################
# ######################## TOOLS ##########################
# #########################################################

def reset_session() -> NotteSession:
    global session
    global current_step
    if session:
        try:
            session.stop()
        except:
            pass
    session = None
    current_step = 0
    session = NotteSession(
        headless=True,  # Force headless mode for server environment
        perception_type="fast",
    )
    session.start()
    return session

def get_session() -> NotteSession:
    global session
    if session is None:
        return reset_session()
    return session

@mcp.tool(description="Start a new local browser session using Notte")
async def notte_start_session(
    headless: Annotated[bool, "Whether to run browser in headless mode"] = False,
    url: Annotated[str | None, "Initial URL to navigate to"] = None,
) -> str:
    """Start a new local Notte session"""
    global session
    if session:
        try:
            session.stop()
        except:
            pass
    
    session = NotteSession(
        headless=True,  # Force headless mode for server environment
        perception_type="fast",
    )
    session.start()
    
    if url:
        try:
            session.execute({"type": "goto", "url": url})
            return f"Local session started and navigated to {url}"
        except Exception as e:
            return f"Local session started but failed to navigate to {url}: {e}"
    
    return "Local session started successfully"



@mcp.tool(description="Stop the current local session")
async def notte_stop_session() -> str:
    """Stop the current local session"""
    global session
    if session:
        try:
            session.stop()
            session = None
            return "Local session stopped successfully"
        except Exception as e:
            session = None
            return f"Session stopped with error: {e}"
    return "No active session to stop"

@mcp.tool(description="Navigate to a URL in the current session")
async def notte_goto(
    url: Annotated[str, "The URL to navigate to"],
) -> str:
    """Navigate to a URL"""
    session = get_session()
    try:
        result = session.execute({"type": "goto", "url": url})
        global current_step
        current_step += 1
        return f"Successfully navigated to {url}"
    except Exception as e:
        return f"Failed to navigate to {url}: {e}"


@mcp.tool(
    description="""Observe the current page and the available actions on it
    OUTPUT STRUCTURE:
    1. Current URL: The webpage you're currently on
    2. Available Tabs: List of open browser tabs
    3. Interactive Elements: List in the format:
    id[:]<element_type>element_text</element_type>
    - `id`: identifier for interaction. `ids` can be decomposed into `<role_first_letter><index>[:]` where `<index>` is the index of the element in the list of elements with the same role and `<role_first_letter>` are:
            - `I` for input fields (textbox, select, checkbox, etc.)
            - `B` for buttons
            - `L` for links
            - `F` for figures and images
            - `O` for options in select elements
            - `M` for miscellaneous elements (e.g. modals, dialogs, etc.) that are only clickable for the most part.
    - `element_type`: HTML element type (button, input, etc.)
    - `element_text`: Visible text or element description

    Example:
    B1[:]<button>Submit Form</button>
    _[:] Non-interactive text
    Notes:
    - Only elements with `ids` are interactive
    - `_[:]` elements provide context but cannot be interacted with
    """
)
async def notte_observe() -> ObservationToolResponse:
    """Observe the current page and the available actions on it
    OUTPUT STRUCTURE:
    1. Current URL: The webpage you're currently on
    2. Available Tabs: List of open browser tabs
    3. Interactive Elements: List in the format:
    id[:]<element_type>element_text</element_type>
    - `id`: identifier for interaction. `ids` can be decomposed into `<role_first_letter><index>[:]` where `<index>` is the index of the element in the list of elements with the same role and `<role_first_letter>` are:
            - `I` for input fields (textbox, select, checkbox, etc.)
            - `B` for buttons
            - `L` for links
            - `F` for figures and images
            - `O` for options in select elements
            - `M` for miscellaneous elements (e.g. modals, dialogs, etc.) that are only clickable for the most part.
    - `element_type`: HTML element type (button, input, etc.)
    - `element_text`: Visible text or element description

    Example:
    B1[:]<button>Submit Form</button>
    _[:] Non-interactive text
    Notes:
    - Only elements with `ids` are interactive
    - `_[:]` elements provide context but cannot be interacted with
    """
    session = get_session()
    obs = await session.aobserve(perception_type="fast")
    snapshot = session.snapshot
    # Use basic markdown rendering instead of agent perception
    observation = DomNodeRenderingPipe.forward(snapshot.dom_node, DomNodeRenderingType.MARKDOWN, include_ids=True)
    return ObservationToolResponse(
        observation=observation,
        code="session.observe()",
    )



@mcp.tool(
    description="Takes a screenshot of the current page. Use this tool to save image of current browser only with format (.png)"
)
def notte_screenshot(path_to_save: str) -> str:
    """Takes a screenshot of the current page"""
    session = get_session()
    response = session.observe(perception_type="fast")
    data = response.screenshot.bytes()
    image = image_from_bytes(data)
    image.save(path_to_save)
    # with open(path_to_save, "wb") as f:
    #     f.write(base64.b64decode(obj.data))
    return f"Capture and save the image to {path_to_save}."


@mcp.tool(
    description="Take a click to object on the current page. Use `notte_observe` first to list the available actions and id of elements. Please use nested dict arguments to call this action"
)
def click(
    id: str
) -> ExecutionToolResponse:
    """
        Take a click to object on the current page
    """
    action=ClickAction(type='click', id=id)
    session = get_session()
    result = session.execute(action=action)
    global current_step
    current_step += 1
    return ExecutionToolResponse(
        result=result,
        code=f"session.execute({result.action.model_dump_agent(include_selector=True)})",
    )

@mcp.tool(
    description="Fill an input field with a value. Use `notte_observe` first to list the available actions and id of elements."
)
def fill(
    # action: FillAction
    id: str,
    value: str,
    press_enter: bool=True
) -> ExecutionToolResponse:
    """
        Fill an input field with a value
    """
    action = FillAction(
        id=id,
        value=value,
        press_enter=press_enter,
        type='fill'
    )
    session = get_session()
    result = session.execute(action=action)
    global current_step
    current_step += 1
    return ExecutionToolResponse(
        result=result,
        code=f"session.execute({result.action.model_dump_agent(include_selector=True)})",
    )


# @mcp.tool(
#     description="Perform scroll down"
# )
# def scroll_down():
#     pass

@mcp.tool(
    description="Check a checkbox. Use value is `True` to check, `False` to uncheck. Please use nested dict arguments to call this action"
)
def check(
    id: str,
    value: bool
) -> ExecutionToolResponse:
    """
       Check a checkbox. Use value is `True` to check, `False` to uncheck. Please use nested dict arguments to call this action
    """
    action=CheckAction(type='check', id=id, value=value)
    session = get_session()
    result = session.execute(action=action)
    global current_step
    current_step += 1
    return ExecutionToolResponse(
        result=result,
        code=f"session.execute({result.action.model_dump_agent(include_selector=True)})",
    )


@mcp.tool(
    description="Wait for a given amount of time (in milliseconds)",
)
def wait(time_ms: int):
    action = WaitAction(type='wait', time_ms=time_ms)
    session = get_session()
    result = session.execute(action=action)
    global current_step
    current_step += 1
    return ExecutionToolResponse(
        result=result,
        code=f"session.execute({result.action.model_dump_agent(include_selector=True)})",
    )

@mcp.tool(
    description="Press a keyboard key: e.g. 'Enter', 'Backspace', 'Insert', 'Delete', etc."
)
def press_key(
    key: str
):
    action = PressKeyAction(type='press_key', key=key)
    session = get_session()
    result = session.execute(action=action)
    global current_step
    current_step += 1
    return ExecutionToolResponse(
        result=result,
        code=f"session.execute({result.action.model_dump_agent(include_selector=True)})",
    )

@mcp.tool(
    description="Scroll up by a given amount of pixels. Use `null` for scrolling up one page"
)
def scroll_up(
    amount: int=None
):
    action = ScrollUpAction(type='scroll_up', amount=amount)
    session = get_session()
    result = session.execute(action=action)
    global current_step
    current_step += 1
    return ExecutionToolResponse(
        result=result,
        code=f"session.execute({result.action.model_dump_agent(include_selector=True)})",
    )

@mcp.tool(
    description="Scroll down by a given amount of pixels. Use `null` for scrolling down one page"
)
def scroll_down(
    amount: int=None
):
    action = ScrollDownAction(type='scroll_down', amount=amount)
    session = get_session()
    result = session.execute(action=action)
    global current_step
    current_step += 1
    return ExecutionToolResponse(
        result=result,
        code=f"session.execute({result.action.model_dump_agent(include_selector=True)})",
    )



# class ScrollDownAction(BrowserAction):
#     type: Literal["scroll_down"] = "scroll_down"  # pyright: ignore [reportIncompatibleVariableOverride]
#     description: str = "Scroll down by a given amount of pixels. Use `null` for scrolling down one page"
#     # amount of pixels to scroll. None for scrolling down one page
#     amount: int | None = None

#     @override
#     def execution_message(self) -> str:
#         return f"Scrolled down by {str(self.amount) + ' pixels' if self.amount is not None else 'one page'}"

#     @override
#     @staticmethod
#     def example() -> "ScrollDownAction":
#         return ScrollDownAction(amount=None)

#     @property
#     @override
#     def param(self) -> ActionParameter | None:
#         return ActionParameter(name="amount", type="int")

if __name__ == "__main__":
    mcp.run(transport='http', host='0.0.0.0', port=6060)