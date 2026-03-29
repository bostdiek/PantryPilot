"""Query templates for each persona.

These templates represent realistic user queries that personas would make,
including variable placeholders, edge cases, and multi-turn conversation
scenarios for training data generation.

TOOL COVERAGE (from agent.py):
1. get_meal_plan_history - "What did I make last week?"
2. search_recipes - "Find me a quick chicken dinner"
3. get_recipe_details - "Show me full ingredients and steps for that recipe"
4. get_daily_weather - "What's the weather like?" / "Something warm for this cold day"
5. web_search - "Find me a recipe for beef wellington online"
6. fetch_url_as_markdown - "Get that recipe from allrecipes.com"
7. suggest_recipe - "Save this recipe for later"
8. propose_meal_for_day - "Add chicken to Monday's dinner"
9. update_user_memory - Implicit through personal info sharing
"""

from typing import Any


# Query templates for each persona covering ALL agent tools
PERSONA_QUERIES: dict[str, list[str]] = {
    "veggie_val": [
        # search_recipes - recipe discovery
        "I want to make something with tofu tonight",
        "Can you suggest a Mediterranean dish?",
        "What vegetarian dishes use quinoa?",
        "I'm craving Italian food - any suggestions?",
        "Show me recipes under 30 minutes",
        # get_recipe_details - request full single-recipe details
        "Show me full ingredients and steps for the first recipe",
        # get_meal_plan_history - history queries
        "What did I make last Tuesday?",
        "What have I been eating this month?",
        "Show me my meal history for the past week",
        # get_daily_weather - weather-based suggestions
        "What's the weather like in San Francisco today?",
        "What should I cook based on today's weather?",
        "Can you check the weather and suggest something appropriate?",
        # web_search - find new recipes online
        "Find me a new vegetarian recipe online",
        "Search the web for tofu stir fry recipes",
        "Look up Mediterranean chickpea recipes",
        # fetch_url_as_markdown - get specific recipe
        "Get the recipe from minimalistbaker.com/vegan-curry",
        "Fetch the Buddha bowl recipe from ohsheglows.com",
        # suggest_recipe - save recipe drafts
        "Save a tofu recipe for later",
        "Add the best Buddha bowl recipe to my collection",
        # propose_meal_for_day - meal planning
        "Plan my dinners for next week",
        "Add Chickpea Curry to Monday's dinner",
        "What should I make on Saturday?",
        "Put something vegetarian on Wednesday",
        # update_user_memory (implicit through sharing info)
        "Remember that my partner doesn't like mushrooms",
        "I usually meal prep on Sundays",
        "We're trying to eat more Mediterranean food",
        # Edge cases and irrelevant queries
        "What's the weather like today?",
        "Tell me about the history of vegetarianism",
    ],
    "family_fiona": [
        # search_recipes
        "What can I make that the kids will actually eat?",
        "I need dinner for 5, under 30 minutes",
        "I have ground beef and need to use it",
        "Kid-friendly recipes with chicken",
        "Show me recipes the whole family will like",
        # get_recipe_details
        "Can you show the full recipe card for that one?",
        # get_meal_plan_history
        "What did we have last week?",
        "It's Taco Tuesday, remind me what we usually do",
        "Show me what we've eaten this month",
        # get_daily_weather
        "What's the weather like in Columbus today?",
        "Check the weather - should we do comfort food or something light?",
        "What's the forecast for Saturday? Planning a family dinner.",
        # web_search
        "Find me new kid-friendly recipes online",
        "Search for easy school night dinners",
        "Look up crockpot family meals",
        # fetch_url_as_markdown
        "Get that mac and cheese recipe from tasty.co",
        # suggest_recipe
        "Save a chicken nuggets recipe",
        # propose_meal_for_day
        "Help me plan dinners for the whole week",
        "Add mac and cheese to Tuesday's dinner",
        "We're eating out Friday, plan around that",
        "Put lasagna on Sunday - it's our family tradition",
        # update_user_memory
        "Tommy hates broccoli but loves carrots",
        "Remember we always do Taco Tuesday",
        "Soccer practice is Thursday, we need quick dinners",
        "My youngest is allergic to peanuts",
        # Edge cases
        "How do I get my kids to eat healthier?",
        "My kids are so picky, what do I do?",
    ],
    "solo_sam": [
        # search_recipes
        "Quick dinner, don't want to cook much",
        "Something I can make with what I have",
        "Easy recipe using eggs",
        "What's the fastest thing I can cook?",
        "Single portion meals",
        # get_recipe_details
        "Pull the full ingredients and instructions for that option",
        # get_meal_plan_history
        "What did I eat last week?",
        "I think I made ramen recently, when was that?",
        # get_daily_weather
        "What's the weather like in Seattle?",
        "Check the weather - soup weather or salad weather?",
        "What's the forecast for tonight?",
        # web_search
        "Find quick single-serving recipes online",
        "Search for easy microwave meals",
        "Look up instant ramen upgrades",
        # fetch_url_as_markdown
        "Get that ramen recipe from seriouseats.com",
        # suggest_recipe
        "Save a quick lazy dinner recipe",
        # propose_meal_for_day
        "Just plan tomorrow's dinner",
        "Add something quick for Wednesday",
        "I don't really plan ahead, but help me anyway",
        # update_user_memory
        "I hate leftovers, don't suggest anything big",
        "I usually cook around 7pm after work",
        "I only have a small kitchen",
        # Edge cases
        "How long does food last in the fridge?",
        "I never plan ahead",
        "I've got 15 minutes, what can I make?",
    ],
    "gluten_free_grace": [
        # search_recipes
        "GF pasta alternatives",
        "Quick gluten-free dinner",
        "Rice-based dinner ideas",
        "GF Italian food options",
        "What GF recipes do I have?",
        # get_recipe_details
        "Show me the full recipe details for the safest option",
        # get_meal_plan_history
        "What did I make last week that was GF?",
        "Show me my safe meal history",
        "What have I been eating lately?",
        # get_daily_weather
        "What's the weather like in Denver today?",
        "Check the weather - I want to cook something appropriate",
        "What's the forecast? I'm planning a GF meal.",
        # web_search
        "Find gluten-free bread recipes online",
        "Search for celiac-safe Italian recipes",
        "Look up certified GF restaurant recipes",
        # fetch_url_as_markdown
        "Get the GF pizza recipe from kingarthurbaking.com",
        "Fetch the recipe from glutenfreeonashoestring.com",
        # suggest_recipe
        "Save a verified gluten-free pasta recipe",
        "Add a cauliflower crust pizza recipe to my collection",
        # propose_meal_for_day
        "Plan my week with only GF options",
        "Add GF pasta carbonara to Thursday",
        "I need safe dinners for next week",
        # update_user_memory
        "I was diagnosed with celiac 3 years ago",
        "Remember, even cross-contamination is a problem",
        "I'm also avoiding oats unless certified GF",
        "My partner can eat gluten so I cook separate sometimes",
        # Edge cases
        "Is this recipe safe for celiac?",
        "Can I modify this recipe to be gluten-free?",
        "Is oatmeal gluten-free?",
        "What can I substitute for flour?",
    ],
    "adventurous_alex": [
        # search_recipes
        "I want to try making Thai curry from scratch",
        "What's a challenging recipe I haven't tried?",
        "What's the most complex recipe in my collection?",
        "Show me authentic Middle Eastern recipes",
        "Traditional Thai recipes",
        # get_recipe_details
        "Give me full instructions and ingredients for that dish",
        # get_meal_plan_history
        "What did I cook last month?",
        "What cuisines have I been exploring lately?",
        "Show me my cooking adventures this year",
        # get_daily_weather
        "What's the weather like in New York today?",
        "Check the forecast - I want to plan a cooking project",
        "What's the weather this weekend?",
        # web_search
        "Find authentic butter chicken recipe from an Indian chef",
        "Search for traditional ramen recipes from Japan",
        "Look up Moroccan tagine techniques",
        "Find the best Thai green curry recipe online",
        # fetch_url_as_markdown
        "Get that Korean recipe from maangchi.com",
        "Fetch the biryani recipe from seriouseats.com",
        "Grab the technique guide from bonappetit.com",
        # suggest_recipe
        "Save an authentic ramen recipe to my collection",
        "Add a traditional Korean dish to my Japanese collection",
        # propose_meal_for_day
        "Plan a world cuisine tour for next week",
        "Add something Indian for Wednesday's dinner",
        "I want to try a new cuisine each day",
        "Put the homemade ramen on Saturday - I'll need all day",
        # update_user_memory
        "I've mastered Thai cooking, want to try Korean next",
        "I can handle very spicy food",
        "I like to spend weekends on complex recipes",
        "I found an Asian grocery store nearby",
        # Edge cases
        "Teach me a new cuisine - surprise me",
        "Where can I buy specialty ingredients?",
        "I found this ingredient at the Asian market, what do I do with it?",
    ],
    "routine_rita": [
        # search_recipes
        "Show me my usual comfort recipes",
        "Our traditional Sunday roast recipe",
        "The meatloaf recipe we always use",
        "I don't like changes, show me familiar recipes",
        # get_recipe_details
        "Open the full recipe details for the usual Sunday roast",
        # get_meal_plan_history
        "What did we have last week? Do that again",
        "What do we usually have on Mondays?",
        "Show me our weekly rotation",
        "What's our normal schedule?",
        # get_daily_weather
        "What's the weather like in Indianapolis?",
        "Check the weather, though it doesn't change what I cook",
        "What's the forecast for Sunday?",
        # web_search
        "Find a classic meatloaf recipe like grandma made",
        "Search for traditional Sunday roast recipes",
        "Look up old-fashioned pot roast",
        # fetch_url_as_markdown
        "Get the Betty Crocker meatloaf recipe from bettycrocker.com",
        "Fetch the traditional pot roast from allrecipes.com",
        # suggest_recipe
        "Save a classic comfort food recipe",
        "Add a traditional roast recipe to my regulars",
        # propose_meal_for_day
        "Same meal plan as last week please",
        "Make my usual Sunday dinner",
        "Repeat last month's meal plan",
        "It's Sunday, you know what I need",
        "I want my comfort food rotation",
        "Don't suggest anything new, just the regulars",
        # update_user_memory
        "Remember, we ALWAYS have Sunday Roast on Sundays",
        "Taco Tuesday is a family tradition",
        "I don't like new recipes - stick to the classics",
        "We've been doing this rotation for 10 years",
        # Edge cases
        "I'm bored of the same thing",
        "Should I try something new?",
    ],
    "fitness_frank": [
        # search_recipes
        "High protein, low carb",
        "30g+ protein per serving",
        "Lean protein sources",
        "What are my high-protein recipes?",
        "Clean eating recipes",
        # get_recipe_details
        "Show the full recipe so I can check ingredients and steps",
        # get_meal_plan_history
        "What did I have for breakfast yesterday?",
        "How much protein have I been getting this week?",
        "Show me my meal prep history",
        # get_daily_weather
        "What's the weather like in Austin today?",
        "Check the forecast - planning outdoor meal prep",
        "What's the weather this weekend?",
        # web_search
        "Find high-protein meal prep recipes online",
        "Search for bodybuilding meal recipes",
        "Look up lean bulk diet recipes",
        # fetch_url_as_markdown
        "Get the chicken meal prep recipe from fitnessvolt.com",
        "Fetch the protein pancake recipe from muscleandstrength.com",
        # suggest_recipe
        "Save a high-protein meal prep recipe",
        "Add a great macro-friendly recipe to my rotation",
        # propose_meal_for_day
        "Plan my meal prep for the entire week",
        "I need 6 meals a day planned",
        "Add grilled chicken to all my lunches this week",
        "Post-workout meal for tomorrow",
        "Pre-made lunches for gym week",
        # update_user_memory
        "I need 180g protein daily",
        "I'm on a lean bulk right now",
        "Gym days are Monday, Wednesday, Friday",
        "I meal prep every Sunday for the week",
        # Edge cases
        "How much protein do I need?",
        "Best pre-workout snacks",
        "Meal prep ideas for muscle gain",
    ],
    "dairy_free_dana": [
        # search_recipes
        "Creamy without cream",
        "Coconut milk recipes",
        "What dairy-free recipes do I have?",
        "Plant-based recipes",
        "Vegan mac and cheese",
        # get_recipe_details
        "Show me complete ingredients and instructions for that recipe",
        # get_meal_plan_history
        "What did I cook last Tuesday?",
        "Show me what I've been making lately",
        "What dairy-free meals have I had this month?",
        # get_daily_weather
        "What's the weather like in Portland today?",
        "Check the forecast - planning my meals",
        "What's the weather this week?",
        # web_search
        "Find cashew cream pasta recipes online",
        "Search for dairy-free Italian recipes",
        "Look up vegan comfort food",
        # fetch_url_as_markdown
        "Get the vegan cheese sauce recipe from minimalistbaker.com",
        "Fetch the dairy-free mac and cheese from ohsheglows.com",
        # suggest_recipe
        "Save a verified dairy-free pasta recipe",
        "Add a good dairy alternative recipe to my collection",
        # propose_meal_for_day
        "Plan dairy-free dinners for the week",
        "Add coconut curry to Wednesday",
        "I need lactose-free options all week",
        # update_user_memory
        "I'm lactose intolerant and vegetarian",
        "Oat milk is my favorite dairy substitute",
        "My partner can have dairy, so sometimes I adapt",
        "Cashew cream is my go-to for creamy dishes",
        "I react badly to even small amounts of dairy",
        # Edge cases
        "Is ghee dairy-free?",
        "Hidden dairy in foods",
        "Non-dairy cheese alternatives",
        "What can I substitute for milk/butter/cheese?",
    ],
}


# Multi-turn conversation scenarios - each is a flow of queries for realistic dialogues
# These cover ALL 9 tools from agent.py:
# 1. get_meal_plan_history, 2. search_recipes, 3. get_recipe_details,
# 4. get_daily_weather, 5. web_search, 6. fetch_url_as_markdown,
# 7. suggest_recipe, 8. propose_meal_for_day, 9. update_user_memory
CONVERSATION_SCENARIOS: dict[str, list[list[str]]] = {
    "veggie_val": [
        # Full meal planning flow (propose_meal_for_day + search_recipes + history)
        [
            "Help me plan my dinners for next week",
            "What did I make last week so I don't repeat?",
            "Start with something Mediterranean on Monday",
            "That sounds good, add it to Monday",
            "And for Tuesday, something Asian",
            "Perfect, add the stir fry to Tuesday",
        ],
        # Weather-based cooking (get_daily_weather + search_recipes)
        [
            "What's the weather like in San Francisco today?",
            "Based on that, what should I cook?",
            "What's a good warming vegetarian dish?",
            "The lentil soup sounds perfect",
            "Add it to tonight's dinner",
        ],
        # Web recipe import flow (web_search + fetch_url + suggest_recipe)
        [
            "Find me a new vegetarian curry recipe online",
            "That one from Minimalist Baker looks good",
            "Get the full recipe from that page",
            "Save it to my collection",
        ],
        # Memory update flow (update_user_memory + search_recipes)
        [
            "My partner just told me they don't like mushrooms",
            "Can you remember that for future suggestions?",
            "Now show me recipes without mushrooms",
        ],
    ],
    "family_fiona": [
        # Complete weekly planning (history + propose_meal_for_day + weather)
        [
            "Let's plan the whole week",
            "What's the weather looking like in Columbus?",
            "What did we have last week?",
            "Ok, let's start fresh - Monday needs to be quick",
            "Add chicken nuggets to Monday",
            "Tuesday is always Taco Tuesday",
            "Wednesday let's do pasta",
            "Add spaghetti to Wednesday",
        ],
        # Web discovery and save (web_search + fetch_url + suggest_recipe + propose)
        [
            "Search online for new kid-friendly recipes",
            "That hidden veggie mac and cheese looks promising",
            "Get the recipe from that blog",
            "Save it and add it to Thursday",
        ],
        # Memory and preferences (update_user_memory)
        [
            "Tommy won't eat anything green",
            "Remember that please",
            "And Sarah is allergic to peanuts - critical",
            "Show me safe recipes for the family",
        ],
        # History replay flow
        [
            "What did we have last week?",
            "The kids loved Tuesday's taco night",
            "Let's do exactly the same this week",
            "Copy the whole week",
        ],
    ],
    "solo_sam": [
        # Quick weather-based decision (weather + search + propose)
        [
            "What's the weather like in Seattle right now?",
            "Sounds like soup weather, what do I have?",
            "The ramen upgrade sounds good",
            "That's dinner for tonight",
        ],
        # Minimal planning (propose_meal_for_day)
        [
            "I guess I should plan something",
            "Just tomorrow, I don't plan ahead",
            "Something with eggs",
            "Fine, add the scrambled eggs",
        ],
        # Web quick recipe (web_search + fetch)
        [
            "Find me a quick single-serving recipe online",
            "That 5-minute meal looks perfect",
            "Get it from that page",
        ],
    ],
    "gluten_free_grace": [
        # Safety check with meal planning (search + propose + history)
        [
            "I need to plan GF dinners for the week",
            "What did I make last week?",
            "All of those were safe, let's vary it",
            "Show me GF pasta options",
            "Add the carbonara to Wednesday",
            "What about Friday?",
            "Add the rice flour pizza",
        ],
        # Weather-based with constraints (weather + search)
        [
            "What's the weather like in Denver today?",
            "Sounds cold! Something warm and definitely gluten-free",
            "Is the beef stew safe?",
            "Perfect, that's dinner",
        ],
        # Web research for safety (web_search + fetch)
        [
            "Search for certified gluten-free bread recipes",
            "That King Arthur one looks safe",
            "Get the full recipe",
            "Save it - I verified the ingredients",
        ],
    ],
    "adventurous_alex": [
        # Cuisine exploration with web (web_search + fetch + suggest + propose)
        [
            "I want to try Korean cooking",
            "Search for authentic Korean recipes online",
            "That bibimbap from Maangchi looks authentic",
            "Get the recipe",
            "Save it to my collection",
            "Add it to Saturday - I'll need time",
        ],
        # Weather-inspired adventure (weather + search + history)
        [
            "What's the weather like in New York today?",
            "Cold! Perfect weather for something warming and complex",
            "What challenging recipes haven't I tried?",
            "The homemade ramen sounds perfect",
            "Put it on Sunday - I have all day",
        ],
        # Ingredient exploration (memory + search)
        [
            "I found gochujang at the Korean market",
            "Remember I have access to Korean ingredients now",
            "What can I make with gochujang?",
            "Show me the Korean BBQ recipe",
        ],
        # History review (get_meal_plan_history)
        [
            "What cuisines have I been cooking lately?",
            "Looks like lots of Thai",
            "I should try something Middle Eastern next",
            "Show me Moroccan recipes",
        ],
    ],
    "routine_rita": [
        # Full week repeat (history + propose_meal_for_day)
        [
            "What did we have last week?",
            "Perfect, do exactly that again",
            "Same meal plan as last week",
            "Yes, confirm the whole week",
        ],
        # Weather doesn't matter (weather + routine)
        [
            "What's the weather in Indianapolis?",
            "Doesn't matter, I always make Sunday Roast on Sundays",
            "Add the usual Sunday Roast",
            "And Meatloaf Monday like always",
        ],
        # Traditional recipe search (web_search for classics)
        [
            "Find a classic meatloaf recipe like grandma's",
            "That Betty Crocker one looks traditional",
            "Save it, but I'll probably stick to my usual",
        ],
        # Memory of traditions (update_user_memory)
        [
            "Remember, we've done this rotation for 10 years",
            "Sunday is always roast day",
            "Taco Tuesday is sacred",
            "Never suggest changes to the core rotation",
        ],
    ],
    "fitness_frank": [
        # Full meal prep planning (propose_meal_for_day + history + macros)
        [
            "Let's plan my meal prep for the week",
            "I need about 180g protein per day",
            "What did I prep last week?",
            "More variety this week",
            "Add grilled chicken to all lunches",
            "Salmon for Tuesday and Thursday dinners",
            "Protein pancakes every morning",
        ],
        # Weather and workout (weather + search)
        [
            "What's the weather like in Austin today?",
            "Hot! But still need high protein after the gym",
            "Something light but macro-friendly",
            "The tuna poke bowl sounds perfect",
        ],
        # Web fitness recipes (web_search + fetch + suggest)
        [
            "Find high-protein meal prep recipes online",
            "That bodybuilding chicken recipe looks good",
            "Get the macros from that page",
            "Save it - great protein ratio",
        ],
        # Memory of goals (update_user_memory)
        [
            "I'm starting a lean bulk",
            "Remember I need 180g protein daily",
            "Gym days are Monday, Wednesday, Friday",
            "I need bigger post-workout meals on those days",
        ],
    ],
    "dairy_free_dana": [
        # Weekly planning with restrictions (propose + search + history)
        [
            "Plan my dairy-free dinners for the week",
            "What did I make last week?",
            "Let's not repeat too much",
            "Add coconut curry to Monday",
            "Something Italian for Tuesday",
            "The cashew cream pasta would work",
            "Add it to Tuesday",
        ],
        # Weather and restrictions (weather + search)
        [
            "What's the weather like in Portland today?",
            "Sounds chilly! I want something creamy but dairy-free",
            "The coconut soup sounds perfect",
            "Is that also vegetarian?",
            "Great, that's dinner",
        ],
        # Web recipe for alternatives (web_search + fetch + suggest)
        [
            "Find vegan cheese sauce recipes online",
            "That cashew-based one from Minimalist Baker",
            "Get the full recipe",
            "Save it - perfect for my mac and cheese cravings",
        ],
        # Memory of intolerances (update_user_memory)
        [
            "I react badly to even traces of dairy",
            "Remember this is a health issue, not a preference",
            "Cashew cream is my go-to substitute",
            "And I'm vegetarian too",
        ],
    ],
}


# Follow-up query types for generating varied conversation continuations
FOLLOW_UP_TYPES: dict[str, list[str]] = {
    "refinement": [
        "Something quicker",
        "With {ingredient}",
        "But vegetarian",
        "Under 30 minutes",
        "That uses what I have",
    ],
    "clarification": [
        "What's in that?",
        "How long does it take?",
        "Is that {dietary_restriction} safe?",
        "Do I have the ingredients?",
        "What did you mean by that?",
    ],
    "selection": [
        "Show me the first one",
        "Tell me more about that",
        "Let's go with {recipe_name}",
        "The second option sounds good",
        "What else do you have?",
    ],
    "action": [
        "Add it to my meal plan",
        "Save this recipe",
        "Make it for {day}",
        "Add these ingredients to my list",
        "Show me the full recipe",
    ],
    "history": [
        "What did I make last {time_reference}?",
        "Do that again",
        "Same as last time",
        "What did we have on {day}?",
        "Show me my recent meals",
    ],
}


# Tool coverage mapping - maps query patterns to the 9 agent tools
# Tools from agent.py:
# 1. get_meal_plan_history - meal history queries
# 2. search_recipes - recipe discovery in user's collection
# 3. get_recipe_details - fetch full ingredients/instructions for one recipe
# 4. get_daily_weather - weather-based meal suggestions
# 5. web_search - find recipes online
# 6. fetch_url_as_markdown - get recipe from specific URL
# 7. suggest_recipe - save/draft a recipe for collection
# 8. propose_meal_for_day - add meal to specific day
# 9. update_user_memory - remember user preferences/info
QUERY_TOOL_COVERAGE: dict[str, dict[str, list[str]]] = {
    "veggie_val": {
        "search_recipes": [
            "I want to make something with",
            "Can you suggest",
            "Show me recipes",
            "What vegetarian dishes",
        ],
        "get_recipe_details": [
            "Show me full ingredients and steps",
            "full recipe for that one",
            "pull the full instructions",
        ],
        "get_meal_plan_history": [
            "What did I make last",
            "What have I been eating",
            "Show me my meal history",
        ],
        "get_daily_weather": [
            "It's cold and rainy",
            "What's a good recipe for this weather",
            "Something warming for",
        ],
        "web_search": ["Find me a new", "Search the web for", "Look up"],
        "fetch_url_as_markdown": [
            "Get the recipe from this link",
            "Save that recipe from",
        ],
        "suggest_recipe": ["Save this", "Add this to my collection"],
        "propose_meal_for_day": [
            "Plan my dinners",
            "Add to Monday",
            "What should I make on",
        ],
        "update_user_memory": [
            "Remember that",
            "I usually",
            "We're trying to eat more",
        ],
    },
    "family_fiona": {
        "search_recipes": [
            "What can I make that the kids",
            "I need dinner for",
            "Kid-friendly recipes",
            "Show me recipes the whole family",
        ],
        "get_recipe_details": [
            "show the full recipe card",
            "full ingredients for that one",
            "full instructions for that option",
        ],
        "get_meal_plan_history": [
            "What did we have last week",
            "It's Taco Tuesday",
            "Show me what we've eaten",
        ],
        "get_daily_weather": [
            "It's a cold day in Columbus",
            "Hot day today",
            "Rainy Saturday",
        ],
        "web_search": [
            "Find me new kid-friendly recipes online",
            "Search for easy school night",
            "Look up crockpot family meals",
        ],
        "fetch_url_as_markdown": [
            "Get that mac and cheese recipe",
            "Save the recipe from this Pinterest",
        ],
        "suggest_recipe": [
            "Save this chicken nuggets",
            "Add this to my family favorites",
        ],
        "propose_meal_for_day": [
            "Help me plan dinners for",
            "Add mac and cheese to",
            "Put lasagna on Sunday",
        ],
        "update_user_memory": [
            "Tommy hates broccoli",
            "Remember we always do Taco Tuesday",
            "Soccer practice is Thursday",
            "My youngest is allergic",
        ],
    },
    "solo_sam": {
        "search_recipes": [
            "Quick dinner",
            "Easy recipe using",
            "What's the fastest thing",
            "Single portion meals",
        ],
        "get_recipe_details": [
            "pull the full ingredients",
            "show full instructions",
            "show me the full recipe",
        ],
        "get_meal_plan_history": [
            "What did I eat last week",
            "I think I made ramen recently",
        ],
        "get_daily_weather": [
            "It's pouring in Seattle",
            "Cold and dark tonight",
            "Nice day, maybe",
        ],
        "web_search": [
            "Find quick single-serving recipes",
            "Search for easy microwave",
            "Look up instant ramen upgrades",
        ],
        "fetch_url_as_markdown": [
            "Get that ramen recipe from Serious Eats",
            "Grab the recipe from",
        ],
        "suggest_recipe": [
            "Save this for when I'm feeling lazy",
            "Add this to my quick meals",
        ],
        "propose_meal_for_day": [
            "Just plan tomorrow",
            "Add something quick for Wednesday",
        ],
        "update_user_memory": [
            "I hate leftovers",
            "I usually cook around 7pm",
            "I only have a small kitchen",
        ],
    },
    "gluten_free_grace": {
        "search_recipes": [
            "GF pasta alternatives",
            "Quick gluten-free",
            "Rice-based dinner",
            "What GF recipes do I have",
        ],
        "get_recipe_details": [
            "show me full recipe details",
            "full ingredients and steps",
            "open full recipe for that option",
        ],
        "get_meal_plan_history": [
            "What did I make last week that was GF",
            "Show me my safe meal history",
        ],
        "get_daily_weather": ["Cold day in Denver", "It's snowing", "Nice spring day"],
        "web_search": [
            "Find gluten-free bread recipes",
            "Search for celiac-safe Italian",
            "Look up certified GF",
        ],
        "fetch_url_as_markdown": [
            "Get that GF pizza recipe from King Arthur",
            "Save the recipe from this GF blogger",
        ],
        "suggest_recipe": [
            "Save this - I verified it's safe",
            "Add this cauliflower crust",
        ],
        "propose_meal_for_day": [
            "Plan my week with only GF options",
            "Add GF pasta carbonara to Thursday",
        ],
        "update_user_memory": [
            "I was diagnosed with celiac",
            "Remember, even cross-contamination",
            "I'm also avoiding oats",
            "My partner can eat gluten",
        ],
    },
    "adventurous_alex": {
        "search_recipes": [
            "I want to try making Thai curry",
            "What's a challenging recipe",
            "Show me authentic Middle Eastern",
        ],
        "get_recipe_details": [
            "give me full instructions",
            "show full ingredients list",
            "open the full recipe details",
        ],
        "get_meal_plan_history": [
            "What did I cook last month",
            "What cuisines have I been exploring",
        ],
        "get_daily_weather": [
            "It's freezing in New York",
            "Hot summer day",
            "Rainy weekend",
        ],
        "web_search": [
            "Find authentic butter chicken recipe",
            "Search for traditional ramen recipes",
            "Look up Moroccan tagine techniques",
        ],
        "fetch_url_as_markdown": [
            "Get that Maangchi Korean recipe",
            "Save the recipe from Serious Eats",
        ],
        "suggest_recipe": [
            "Save this, it's a proper authentic recipe",
            "Add this to my Japanese collection",
        ],
        "propose_meal_for_day": [
            "Plan a world cuisine tour",
            "Add something Indian for Wednesday",
            "Put the homemade ramen on Saturday",
        ],
        "update_user_memory": [
            "I've mastered Thai cooking",
            "I can handle very spicy food",
            "I like to spend weekends on complex recipes",
            "I found an Asian grocery store",
        ],
    },
    "routine_rita": {
        "search_recipes": [
            "Show me my usual comfort recipes",
            "Our traditional Sunday roast recipe",
            "familiar recipes",
        ],
        "get_recipe_details": [
            "show the full recipe",
            "full details for the usual one",
            "open full ingredients and steps",
        ],
        "get_meal_plan_history": [
            "What did we have last week",
            "What do we usually have on Mondays",
            "Show me our weekly rotation",
        ],
        "get_daily_weather": [
            "What's the weather in Indianapolis",
            "Typical winter day",
            "It's cold",
        ],
        "web_search": [
            "Find a classic meatloaf recipe like grandma",
            "Search for traditional Sunday roast",
        ],
        "fetch_url_as_markdown": [
            "Get that Betty Crocker recipe",
            "Save the traditional recipe",
        ],
        "suggest_recipe": [
            "Save this - it's close to what we usually make",
            "Add this classic to my regulars",
        ],
        "propose_meal_for_day": [
            "Same meal plan as last week",
            "Make my usual Sunday dinner",
            "Repeat last month's meal plan",
        ],
        "update_user_memory": [
            "Remember, we've done this rotation for 10 years",
            "Sunday is always roast day",
            "Taco Tuesday is sacred",
            "Never suggest changes",
        ],
    },
    "fitness_frank": {
        "search_recipes": [
            "High protein, low carb",
            "30g+ protein per serving",
            "Lean protein sources",
            "Clean eating recipes",
        ],
        "get_recipe_details": [
            "show full recipe so I can check ingredients",
            "open full instructions",
            "full recipe details for that meal",
        ],
        "get_meal_plan_history": [
            "What did I have for breakfast yesterday",
            "How much protein have I been getting",
        ],
        "get_daily_weather": [
            "Hot day in Austin",
            "Nice weather for post-workout",
            "It's gym day",
        ],
        "web_search": [
            "Find high-protein meal prep recipes",
            "Search for bodybuilding meal recipes",
            "Look up lean bulk diet",
        ],
        "fetch_url_as_markdown": [
            "Get that chicken meal prep from Fitness Volt",
            "Save the protein pancake recipe",
        ],
        "suggest_recipe": [
            "Save this - great macros",
            "Add this to my meal prep rotation",
        ],
        "propose_meal_for_day": [
            "Plan my meal prep for the entire week",
            "Add grilled chicken to all my lunches",
            "Post-workout meal for tomorrow",
        ],
        "update_user_memory": [
            "I need 180g protein daily",
            "I'm on a lean bulk",
            "Gym days are Monday, Wednesday, Friday",
            "I meal prep every Sunday",
        ],
    },
    "dairy_free_dana": {
        "search_recipes": [
            "Creamy without cream",
            "Coconut milk recipes",
            "What dairy-free recipes do I have",
            "Vegan mac and cheese",
        ],
        "get_recipe_details": [
            "show full ingredients and instructions",
            "open full recipe details",
            "full recipe card for that one",
        ],
        "get_meal_plan_history": [
            "What did I cook last Tuesday",
            "Show me what I've been making",
        ],
        "get_daily_weather": [
            "Rainy day in Portland",
            "Cold and gloomy",
            "Nice day for a light Asian",
        ],
        "web_search": [
            "Find cashew cream pasta recipes",
            "Search for dairy-free Italian",
            "Look up vegan comfort food",
        ],
        "fetch_url_as_markdown": [
            "Get that vegan cheese sauce recipe from Minimalist Baker",
            "Save the dairy-free mac and cheese",
        ],
        "suggest_recipe": [
            "Save this - verified dairy-free",
            "Add this to my dairy alternatives",
        ],
        "propose_meal_for_day": [
            "Plan dairy-free dinners for the week",
            "Add coconut curry to Wednesday",
        ],
        "update_user_memory": [
            "I'm lactose intolerant and vegetarian",
            "Oat milk is my favorite",
            "Cashew cream is my go-to",
            "I react badly to even small amounts",
        ],
    },
}


def get_persona_queries(persona_name: str) -> list[str]:
    """Get query templates for a persona.

    Args:
        persona_name: Name of the persona (e.g., "veggie_val")

    Returns:
        List of query template strings

    Raises:
        KeyError: If persona name is not found
    """
    return PERSONA_QUERIES[persona_name]


def get_conversation_scenarios(persona_name: str) -> list[list[str]]:
    """Get multi-turn conversation scenarios for a persona.

    Args:
        persona_name: Name of the persona

    Returns:
        List of conversation scenarios, each a list of queries in order

    Raises:
        KeyError: If persona name is not found
    """
    return CONVERSATION_SCENARIOS[persona_name]


def get_all_queries() -> dict[str, list[str]]:
    """Get all query templates for all personas.

    Returns:
        Dictionary mapping persona names to query lists
    """
    return PERSONA_QUERIES


def get_tool_coverage_queries(persona_name: str, tool_name: str) -> list[str]:
    """Get queries that should trigger a specific tool for a persona.

    Args:
        persona_name: Name of the persona
        tool_name: Name of the tool (e.g., "search_recipes")

    Returns:
        List of query templates for that tool

    Raises:
        KeyError: If persona or tool name is not found
    """
    return QUERY_TOOL_COVERAGE[persona_name][tool_name]


def get_follow_ups(follow_up_type: str) -> list[str]:
    """Get follow-up query templates by type.

    Args:
        follow_up_type: Type of follow-up (refinement, clarification, etc.)

    Returns:
        List of follow-up templates

    Raises:
        KeyError: If follow-up type is not found
    """
    return FOLLOW_UP_TYPES[follow_up_type]


def format_query(query_template: str, variables: dict[str, Any]) -> str:
    """Format a query template with variable values.

    Args:
        query_template: Template string with {variable} placeholders
        variables: Dictionary of variable names to values

    Returns:
        Formatted query string

    Example:
        >>> format_query("I have {pantry_item} to use", {"pantry_item": "tofu"})
        'I have tofu to use'
    """
    return query_template.format(**variables)
