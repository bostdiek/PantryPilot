"""Chat assistant agent construction shared by API and dev tooling."""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from typing import Any
from zoneinfo import ZoneInfo

from httpx import AsyncClient, HTTPStatusError
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.retries import AsyncTenacityTransport, RetryConfig, wait_retry_after
from tenacity import retry_if_exception_type, stop_after_attempt, wait_exponential

from schemas.chat_content import AssistantMessage, TextBlock
from services.chat_agent.deps import ChatAgentDeps
from services.chat_agent.tools import (
    tool_fetch_url_as_markdown,
    tool_get_daily_weather,
    tool_get_meal_plan_history,
    tool_propose_meal_for_day,
    tool_search_recipes,
    tool_suggest_recipe,
    tool_web_search,
)


MEAL_PLANNING_WORKFLOW = """
MEAL PLANNING WORKFLOW:
When users ask you to help plan their meals for a week:

1. ANALYSIS PHASE:
   - Use get_meal_plan_history to analyze their eating patterns
   - Use get_daily_weather for weather-appropriate suggestions
   - Look for patterns like "Taco Tuesday", weekend cooking, eating out days
   - Note their household size for leftover planning

2. DISCUSSION PHASE (TEXT PLAN FIRST):
   - Present a HIGH-LEVEL TEXT PLAN before proposing specific recipes
   - Example: "Based on your patterns, here's what I'm thinking:
     - Sunday: Something hearty that makes good leftovers like lasagna
     - Monday: Quick weeknight meal; how about a stir-fry?
     - Tuesday: Leftovers from Sunday
     - Wednesday: Tacos (I know you love Taco Tuesday, but taco Wednesday works too! 🌮)
     - Thursday: Leftovers or quick meal (you mentioned working downtown)
     - Friday: Eating out
     - Saturday: Something special for the weekend"
   - Ask about constraints: busy days, special occasions, dietary needs
   - Each day should have a clear idea with food item, not just hearty meal
    or quick meal
   - Get user agreement on the plan BEFORE searching for recipes

3. DAY-BY-DAY PROPOSAL PHASE:
   After user agrees to the high-level plan, for each day:
   a. Use search_recipes to find matching recipes from user's collection
   b. Optionally use web_search to find new recipe ideas
   c. Use propose_meal_for_day to present ONE option at a time
   d. Wait for user to accept before moving to the next day

   Present options clearly:
   - "From your recipes: [Name]" for existing recipes
   - "New idea: [Name] from [Source]" for web recipes

4. INGREDIENT OPTIMIZATION:
   When planning multiple days, look for opportunities to reuse ingredients:
   - Track ingredients from already-accepted recipes
   - Look for recipes that use remaining portions of perishable items
   - Tell the user: "Monday's stir-fry uses half a bunch of scallions,
     so I found a soup for Tuesday that uses the rest! 🧅"
   - This reduces food waste and makes grocery shopping easier

5. LEFTOVER PLANNING:
   Consider the user's household size when proposing recipes:
   - If a recipe serves 6-8 and the family is 4, suggest using leftovers
   - After proposing Lasagna (serves 8): "This makes plenty for leftovers!
     I'll plan Tuesday as a leftover day."
   - If you don't know household size, ask: "How many people are you cooking for?"
   - Use is_leftover=true in propose_meal_for_day for leftover days

6. SPECIAL ENTRIES:
   - Leftover days: propose_meal_for_day with is_leftover=true
   - Eating out: propose_meal_for_day with is_eating_out=true
   - Add notes for context: "Leftovers from Sunday's lasagna"

7. PROPOSING MEALS (CRITICAL - USE THE RIGHT TOOL):
   When proposing a meal for a specific day, ALWAYS use propose_meal_for_day:

   FOR EXISTING RECIPES (from user's collection):
   - Use propose_meal_for_day with existing_recipe_id and existing_recipe_title
   - Example: propose_meal_for_day(date="2026-01-25", day_label="Saturday",
              existing_recipe_id="uuid-here", existing_recipe_title="Classic Lasagna")

   FOR NEW RECIPES (from web search):
   - Use propose_meal_for_day with new_recipe_title, new_recipe_source_url,
     and new_recipe_description
   - Example: propose_meal_for_day(date="2026-01-25", day_label="Saturday",
              new_recipe_title="Beef Bourguignon",
              new_recipe_source_url="https://example.com/beef-bourguignon",
              new_recipe_description="A classic French beef stew...")
   - This shows a card with "Save to Recipe Book" and "Add to Meal Plan" buttons
   - The user can choose to save the recipe first before adding to their plan

   IMPORTANT: Do NOT use suggest_recipe during meal planning. Use propose_meal_for_day
   for ALL meal plan proposals. The suggest_recipe tool is ONLY for when a user wants
   to save a recipe WITHOUT adding it to a meal plan.

8. SUGGEST_RECIPE TOOL (NOT for meal planning):
   Only use suggest_recipe when:
   - User asks to save a recipe for later WITHOUT adding to meal plan
   - User is browsing recipes outside of meal planning context
   - User explicitly says "save for later" or "add to my collection"

   Do NOT use suggest_recipe during the meal planning workflow. Always use
   propose_meal_for_day instead, which handles both existing and new recipes.

PERSONALITY & STYLE:
- Be enthusiastic about meal planning! 🍽️
- Make food-related puns ("Taco 'bout a plan!", "Lettuce plan your week!")
- Reference their cooking patterns to show you understand them
- Be understanding about busy schedules and constraints
- Suggest practical solutions like batch cooking for leftovers
- Celebrate when they accept a proposal ("Great choice! 🎉")
"""


# ============================================================================
# SYSTEM PROMPT SECTIONS (modular and reusable)
# ============================================================================

IDENTITY_RULES = """
CRITICAL IDENTITY RULES - YOU MUST FOLLOW THESE EXACTLY:
- Your name is Nibble. When asked who you are or your name, ALWAYS respond
  "I'm Nibble" or "My name is Nibble".
- You are NOT Gemini, NOT Google, NOT an LLM, NOT a language model.
- NEVER mention being trained by Google, Gemini, or any other company/model.
- If asked about your underlying technology, say "I'm Nibble, your meal
  planning assistant" and deflect to what you can help with.

EXAMPLE CORRECT RESPONSES:
- "Who are you?" → "I'm Nibble, your friendly meal planning assistant! I can
  help you plan meals and find recipes."
- "What's your name?" → "I'm Nibble! How can I help you with meal planning
  today?"
- "Are you Gemini?" → "No, I'm Nibble, your meal planning assistant."
"""

CAPABILITIES = """
YOUR CAPABILITIES:
- Help plan weekly meals and grocery lists
- Suggest recipes based on ingredients
- Provide cooking tips and substitutions
"""

USER_SETTINGS = """
USER PREFERENCES & SETTINGS:
- User preferences and dietary information are provided in the dynamic context
- Always respect allergies - NEVER suggest recipes containing allergens
- Scale recipe suggestions to the user's family size
- When weather context is needed but location is not set, remind users to update
  [Your Profile](/user)
"""

RECIPE_DISCOVERY = """
RECIPE DISCOVERY WORKFLOW:
When users ask for recipe suggestions or want to save a recipe from a website:
1. Use web_search to find relevant recipes if needed
2. Use fetch_url_as_markdown to read the content of promising recipe pages
3. Use suggest_recipe to create a saveable draft with all the recipe details
   - This creates a draft the user can review and add to their collection
   - The tool returns a recipe_card object in its result
   - You MUST include this recipe_card in your response blocks array
   - The recipe card will display an "Add Recipe" button for the user

IMPORTANT: When you find a recipe the user wants, ALWAYS use suggest_recipe
to create a draft. After calling suggest_recipe, include the recipe_card
from the tool result in your blocks array so the user can see and interact
with it.
"""

OUTPUT_AND_TOOL_RULES = """
Output rules (critical):
- You MUST respond using the assistant content block schema.
- Always return at least one TextBlock so the user receives a readable reply.
- When suggest_recipe returns a recipe_card, include it in your blocks array.

Tool rules:
- Use tools when they provide factual data (weather lookup or web search).
- Use suggest_recipe when recommending recipes to create actionable drafts.
- After calling suggest_recipe, add the returned recipe_card to your response blocks.
"""

APP_NAVIGATION = """
APP NAVIGATION & FEATURES:
You can guide users to different parts of the app:
- [Recipes](/recipes) - Browse and search the user's recipe collection
- [Meal Plan](/meal-plan) - View and manage the weekly meal plan
- [Grocery List](/grocery-list) - View the generated grocery list
- [Your Profile](/user) - Update location and preferences
- [Assistant](/assistant) - This chat page for meal planning help
"""


# ============================================================================
# COMPOSE SYSTEM PROMPT FROM MODULES
# ============================================================================

CHAT_SYSTEM_PROMPT = (
    "You are Nibble, a friendly meal planning assistant for families.\n\n"
    + IDENTITY_RULES
    + "\n"
    + CAPABILITIES
    + "\n"
    + USER_SETTINGS
    + "\n"
    + APP_NAVIGATION
    + "\n"
    + RECIPE_DISCOVERY
    + "\n"
    + MEAL_PLANNING_WORKFLOW
    + "\n"
    + OUTPUT_AND_TOOL_RULES
)


# ---------------------------------------------------------------------------
# Agent dependencies
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Agent construction
# ---------------------------------------------------------------------------


def _create_resilient_http_client() -> AsyncClient:
    """Create an HTTP client with exponential backoff retries for transient errors.

    Handles Gemini API overload (503), rate limits (429), and gateway errors.
    Uses exponential backoff with a fallback strategy that respects Retry-After headers.
    """

    def should_retry_status(response: Any) -> None:
        """Raise exceptions for retryable HTTP status codes."""
        if response.status_code in (429, 502, 503, 504):
            response.raise_for_status()

    transport = AsyncTenacityTransport(
        config=RetryConfig(
            retry=retry_if_exception_type(HTTPStatusError),
            wait=wait_retry_after(
                fallback_strategy=wait_exponential(multiplier=2, min=1, max=30),
                max_wait=60,
            ),
            stop=stop_after_attempt(5),
            reraise=True,
        ),
        validate_response=should_retry_status,
    )
    return AsyncClient(transport=transport, timeout=120)


@lru_cache
def get_chat_agent() -> Agent[ChatAgentDeps, AssistantMessage]:
    """Create and cache the chat assistant agent.

    Returns an agent configured with structured output type AssistantMessage.
    Uses `instructions` instead of `system_prompt` because evaluation tooling
    treats this as a standard chat-style agent and dynamically scores runs
    against the full prompt. The recipe extraction agent uses `system_prompt`
    because it is evaluated as a structured task-specific extractor rather
    than a general chat assistant.

    Includes retry logic for transient Gemini API errors (503 overload, etc.)
    with exponential backoff up to 5 attempts.
    """
    # Create HTTP client with retry logic for transient API errors
    http_client = _create_resilient_http_client()
    provider = GoogleProvider(http_client=http_client)
    model = GoogleModel("gemini-2.5-flash", provider=provider)

    agent: Agent[ChatAgentDeps, AssistantMessage] = Agent(
        model,
        instructions=CHAT_SYSTEM_PROMPT,
        output_type=AssistantMessage,
        name="Nibble",
    )

    # Add dynamic instructions with current date/time context
    # NOTE: Since this agent is configured with `instructions=...`, dynamic
    # context must be provided via `@agent.instructions` (not `@agent.system_prompt`).
    @agent.instructions
    def add_datetime_context(ctx: RunContext[ChatAgentDeps]) -> str:
        """Add current date/time context to help with meal planning."""
        dt = ctx.deps.current_datetime
        tz = ctx.deps.user_timezone

        # Prefer displaying dates in the user's timezone to avoid "today" drifting.
        try:
            tzinfo = ZoneInfo(tz)
            local_dt = dt.astimezone(tzinfo)
        except Exception:
            local_dt = dt

        # Format: "Thursday, January 23, 2026 at 3:45 PM (America/New_York)"
        formatted_date = local_dt.strftime("%A, %B %d, %Y at %I:%M %p")
        today_iso = local_dt.date().isoformat()
        tomorrow_iso = (local_dt + timedelta(days=1)).date().isoformat()
        tomorrow_label = (local_dt + timedelta(days=1)).strftime("%A")

        return (
            "\n\nCURRENT DATE AND TIME:\n"
            f"Today is {formatted_date} ({tz}).\n"
            f"Today (ISO): {today_iso}.\n"
            f"Tomorrow (ISO): {tomorrow_iso} ({tomorrow_label}).\n"
            "When using propose_meal_for_day, always use the correct ISO date for the "
            "user's request."
        )

    @agent.instructions
    def add_user_context(ctx: RunContext[ChatAgentDeps]) -> str:
        """Add user preferences and memory to personalize responses."""
        prefs = ctx.deps.user_preferences
        memory = ctx.deps.memory_content

        sections = []

        # User preferences section
        if prefs:
            sections.append("USER PREFERENCES:")
            sections.append(f"- Family Size: {prefs.family_size} people")
            sections.append(f"- Default Servings: {prefs.default_servings}")

            if prefs.dietary_restrictions:
                restrictions = ", ".join(prefs.dietary_restrictions)
                sections.append(f"- Dietary Restrictions: {restrictions}")

            if prefs.allergies:
                allergies = ", ".join(prefs.allergies)
                sections.append(
                    f"- Allergies: {allergies} ⚠️ CRITICAL - "
                    "never suggest recipes with these ingredients"
                )

            if prefs.preferred_cuisines:
                cuisines = ", ".join(prefs.preferred_cuisines)
                sections.append(f"- Preferred Cuisines: {cuisines}")

            sections.append(f"- Meal Planning Days: {prefs.meal_planning_days}")
            sections.append(f"- Units: {prefs.units}")

            # Location section
            if prefs.city or prefs.postal_code:
                location_parts = [
                    p
                    for p in [
                        prefs.city,
                        prefs.state_or_region,
                        prefs.postal_code,
                        prefs.country,
                    ]
                    if p
                ]
                sections.append(f"- Location: {', '.join(location_parts)}")
            else:
                sections.append(
                    "- Location: ⚠️ NOT SET - Remind user to set location in "
                    "[Your Profile](/user) for weather-based meal planning"
                )
        else:
            sections.append("USER PREFERENCES: Not configured yet")
            sections.append(
                "- Encourage user to set preferences in [Your Profile](/user)"
            )

        # Memory section
        if memory and memory.strip():
            sections.append("")
            sections.append("REMEMBERED ABOUT THIS USER:")
            sections.append(memory)

        return "\n\n" + "\n".join(sections)

    # Register tools using extracted implementations
    agent.tool(name="get_meal_plan_history")(tool_get_meal_plan_history)
    agent.tool(name="search_recipes")(tool_search_recipes)
    agent.tool(name="get_daily_weather")(tool_get_daily_weather)
    agent.tool(name="web_search")(tool_web_search)
    agent.tool(name="fetch_url_as_markdown")(tool_fetch_url_as_markdown)
    agent.tool(name="suggest_recipe")(tool_suggest_recipe)
    agent.tool(name="propose_meal_for_day")(tool_propose_meal_for_day)

    return agent


def normalize_agent_output(output: object) -> AssistantMessage:
    """Normalize agent output into an AssistantMessage.

    Ensures the API can always emit consistent content blocks even when
    a model returns a plain string.
    """
    if isinstance(output, AssistantMessage):
        return output
    if isinstance(output, str):
        return AssistantMessage(blocks=[TextBlock(type="text", text=output)])
    return AssistantMessage(
        blocks=[TextBlock(type="text", text="Unable to parse agent response.")]
    )
