from ii_agent.tools.base import ToolImplOutput


def format_screenshot_tool_output(screenshot: str, msg: str) -> ToolImplOutput:
    return ToolImplOutput(
        tool_output=[
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": screenshot,
                },
            },
            {"type": "text", "text": msg},
        ],
        tool_result_message=msg,
    )

def format_html_tool_output(html: str, msg: str) -> ToolImplOutput:
    return ToolImplOutput(
        tool_output=[
            {
                "type": "text",
                "text": html,
            },
            {"type": "text", "text": msg},
        ],
        tool_result_message=msg,
    )
