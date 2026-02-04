from langchain_core.tools import Tool
from typing import Optional

class HumanInteractionTool:
    """Tool for clarifying information from the user"""

    def __init__(self):
        self.last_question = None

    def ask(self, question: str, options: Optional[list] = None) -> str:
        self.last_question = question

        print(f"\n🤖 Agent: {question}")

        if options:
            for i, opt in enumerate(options, 1):
                print(f"   {i}. {opt}")

        response = input("\nYou: ").strip()

        if options and response.isdigit():
            idx = int(response) - 1
            if 0 <= idx < len(options):
                response = options[idx]

        return response


human_tool = HumanInteractionTool()

ask_human_tool = Tool(
    name="ask_human",
    func=human_tool.ask,
    description="""
Clarify information from the user.

Use when:
- Missing key information (destination, dates, budget, number of people)
- A choice between options is required
- Confirmation is required before final recommendation

Input:
- question (string)
- optional options (list)

Output:
- user's answer (string)
"""
)
