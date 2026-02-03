"""User personas for synthetic training data generation.

This module defines diverse user personas for generating realistic training data
covering various dietary preferences, household types, and cooking styles.
"""

from typing import TypedDict


class PersonaLocation(TypedDict):
    """Location data for weather-based meal planning."""

    city: str
    state_or_region: str
    country: str
    postal_code: str


class PersonaPreferences(TypedDict):
    """User preferences for a persona."""

    dietary_restrictions: list[str]
    cuisine_preferences: list[str]
    cooking_skill: str  # "beginner" | "intermediate" | "advanced"
    household_size: int
    has_picky_eaters: bool | None  # Optional
    hates_leftovers: bool | None  # Optional
    location: PersonaLocation  # Required for weather tool


class RecipeData(TypedDict):
    """Recipe data for persona's collection."""

    name: str
    tags: list[str]


class MealPlanHistoryEntry(TypedDict):
    """Meal plan history entry."""

    date: str  # Format: "YYYY-MM-DD"
    meal: str  # "breakfast" | "lunch" | "dinner"
    recipe: str


class PersonaProfile(TypedDict):
    """Complete profile for a user persona."""

    user_id: str
    preferences: PersonaPreferences
    recipes: list[RecipeData]
    meal_plan_history: list[MealPlanHistoryEntry]
    pantry_items: list[str]


# 8 diverse personas covering different dietary needs and household types
PERSONAS: dict[str, PersonaProfile] = {
    "veggie_val": {
        "user_id": "synthetic-veggie-val",
        "preferences": {
            "dietary_restrictions": ["vegetarian"],
            "cuisine_preferences": ["Mediterranean", "Asian"],
            "cooking_skill": "intermediate",
            "household_size": 2,
            "has_picky_eaters": None,
            "hates_leftovers": None,
            "location": {
                "city": "San Francisco",
                "state_or_region": "California",
                "country": "USA",
                "postal_code": "94102",
            },
        },
        "recipes": [
            {"name": "Chickpea Curry", "tags": ["vegetarian", "indian", "30min"]},
            {"name": "Caprese Salad", "tags": ["vegetarian", "italian", "15min"]},
            {"name": "Mushroom Risotto", "tags": ["vegetarian", "italian", "45min"]},
            {"name": "Veggie Stir Fry", "tags": ["vegetarian", "asian", "20min"]},
            {"name": "Lentil Soup", "tags": ["vegetarian", "comfort", "40min"]},
            {"name": "Pasta Primavera", "tags": ["vegetarian", "italian", "30min"]},
            {"name": "Falafel Bowl", "tags": ["vegetarian", "mediterranean", "30min"]},
            {"name": "Ratatouille", "tags": ["vegetarian", "french", "60min"]},
            {"name": "Spinach and Feta Pie", "tags": ["vegetarian", "greek", "45min"]},
            {"name": "Veggie Burger", "tags": ["vegetarian", "american", "25min"]},
            {"name": "Tofu Scramble", "tags": ["vegetarian", "breakfast", "15min"]},
            {"name": "Vegetable Tempura", "tags": ["vegetarian", "japanese", "30min"]},
            {"name": "Greek Salad", "tags": ["vegetarian", "mediterranean", "10min"]},
            {
                "name": "Stuffed Bell Peppers",
                "tags": ["vegetarian", "comfort", "50min"],
            },
            {"name": "Quinoa Buddha Bowl", "tags": ["vegetarian", "healthy", "25min"]},
            {"name": "Vegetable Pad Thai", "tags": ["vegetarian", "thai", "30min"]},
            {"name": "Minestrone Soup", "tags": ["vegetarian", "italian", "45min"]},
            {"name": "Veggie Lasagna", "tags": ["vegetarian", "italian", "60min"]},
            {
                "name": "Hummus and Veggie Wrap",
                "tags": ["vegetarian", "quick", "10min"],
            },
            {"name": "Eggplant Parmesan", "tags": ["vegetarian", "italian", "50min"]},
            {"name": "Black Bean Tacos", "tags": ["vegetarian", "mexican", "20min"]},
            {"name": "Vegetable Curry", "tags": ["vegetarian", "indian", "35min"]},
            {"name": "Margherita Pizza", "tags": ["vegetarian", "italian", "30min"]},
            {
                "name": "Portobello Mushroom Burger",
                "tags": ["vegetarian", "american", "25min"],
            },
            {"name": "Vegetable Fried Rice", "tags": ["vegetarian", "asian", "20min"]},
        ],
        "meal_plan_history": [
            {"date": "2026-01-20", "meal": "dinner", "recipe": "Chickpea Curry"},
            {"date": "2026-01-21", "meal": "dinner", "recipe": "Pasta Primavera"},
            {"date": "2026-01-22", "meal": "dinner", "recipe": "Veggie Stir Fry"},
            {"date": "2026-01-23", "meal": "dinner", "recipe": "Lentil Soup"},
            {"date": "2026-01-24", "meal": "dinner", "recipe": "Mushroom Risotto"},
            {"date": "2026-01-25", "meal": "dinner", "recipe": "Falafel Bowl"},
            {"date": "2026-01-26", "meal": "dinner", "recipe": "Caprese Salad"},
            {"date": "2026-01-27", "meal": "dinner", "recipe": "Ratatouille"},
            {"date": "2026-01-28", "meal": "dinner", "recipe": "Veggie Burger"},
            {"date": "2026-01-29", "meal": "dinner", "recipe": "Quinoa Buddha Bowl"},
            {"date": "2026-01-30", "meal": "dinner", "recipe": "Vegetable Pad Thai"},
            {"date": "2026-01-31", "meal": "dinner", "recipe": "Black Bean Tacos"},
            {"date": "2026-02-01", "meal": "dinner", "recipe": "Eggplant Parmesan"},
            {"date": "2026-02-02", "meal": "dinner", "recipe": "Veggie Lasagna"},
        ],
        "pantry_items": [
            "chickpeas",
            "lentils",
            "tofu",
            "tempeh",
            "quinoa",
            "rice",
            "olive oil",
            "garlic",
            "onions",
            "tomatoes",
            "spinach",
        ],
    },
    "family_fiona": {
        "user_id": "synthetic-family-fiona",
        "preferences": {
            "dietary_restrictions": [],
            "cuisine_preferences": ["American", "Italian", "Mexican"],
            "cooking_skill": "beginner",
            "household_size": 5,
            "has_picky_eaters": True,
            "hates_leftovers": None,
            "location": {
                "city": "Columbus",
                "state_or_region": "Ohio",
                "country": "USA",
                "postal_code": "43215",
            },
        },
        "recipes": [
            {"name": "Mac and Cheese", "tags": ["kid-friendly", "30min"]},
            {"name": "Chicken Nuggets", "tags": ["kid-friendly", "20min"]},
            {"name": "Spaghetti Bolognese", "tags": ["family", "45min"]},
            {"name": "Taco Tuesday", "tags": ["family", "mexican", "30min"]},
            {"name": "Pizza Night", "tags": ["kid-friendly", "family", "30min"]},
            {"name": "Grilled Cheese", "tags": ["kid-friendly", "10min"]},
            {"name": "Chicken Tenders", "tags": ["kid-friendly", "25min"]},
            {"name": "Hot Dogs", "tags": ["kid-friendly", "quick", "15min"]},
            {"name": "Hamburgers", "tags": ["family", "american", "30min"]},
            {"name": "Meatballs", "tags": ["family", "italian", "40min"]},
            {"name": "Quesadillas", "tags": ["kid-friendly", "mexican", "15min"]},
            {"name": "Chicken and Rice", "tags": ["family", "easy", "35min"]},
            {"name": "Lasagna", "tags": ["family", "italian", "60min"]},
            {"name": "Chili", "tags": ["family", "comfort", "45min"]},
            {"name": "Baked Ziti", "tags": ["family", "italian", "40min"]},
            {"name": "Fish Sticks", "tags": ["kid-friendly", "20min"]},
            {"name": "Corn Dogs", "tags": ["kid-friendly", "quick", "15min"]},
            {"name": "Sloppy Joes", "tags": ["family", "american", "25min"]},
            {"name": "Chicken Alfredo", "tags": ["family", "italian", "30min"]},
            {"name": "Beef Tacos", "tags": ["family", "mexican", "25min"]},
        ],
        "meal_plan_history": [
            {"date": "2026-01-20", "meal": "dinner", "recipe": "Mac and Cheese"},
            {"date": "2026-01-21", "meal": "dinner", "recipe": "Chicken Nuggets"},
            {"date": "2026-01-22", "meal": "dinner", "recipe": "Taco Tuesday"},
            {"date": "2026-01-23", "meal": "dinner", "recipe": "Spaghetti Bolognese"},
            {"date": "2026-01-24", "meal": "dinner", "recipe": "Pizza Night"},
            {"date": "2026-01-25", "meal": "dinner", "recipe": "Grilled Cheese"},
            {"date": "2026-01-26", "meal": "dinner", "recipe": "Hamburgers"},
            {"date": "2026-01-27", "meal": "dinner", "recipe": "Chicken Tenders"},
            {"date": "2026-01-28", "meal": "dinner", "recipe": "Quesadillas"},
            {"date": "2026-01-29", "meal": "dinner", "recipe": "Taco Tuesday"},
            {"date": "2026-01-30", "meal": "dinner", "recipe": "Chicken and Rice"},
            {"date": "2026-01-31", "meal": "dinner", "recipe": "Meatballs"},
            {"date": "2026-02-01", "meal": "dinner", "recipe": "Lasagna"},
            {"date": "2026-02-02", "meal": "dinner", "recipe": "Hot Dogs"},
        ],
        "pantry_items": [
            "pasta",
            "ground beef",
            "chicken breast",
            "cheese",
            "milk",
            "bread",
            "eggs",
            "butter",
            "ketchup",
            "ranch dressing",
        ],
    },
    "solo_sam": {
        "user_id": "synthetic-solo-sam",
        "preferences": {
            "dietary_restrictions": [],
            "cuisine_preferences": ["Quick", "Asian"],
            "cooking_skill": "beginner",
            "household_size": 1,
            "has_picky_eaters": None,
            "hates_leftovers": True,
            "location": {
                "city": "Seattle",
                "state_or_region": "Washington",
                "country": "USA",
                "postal_code": "98101",
            },
        },
        "recipes": [
            {"name": "Ramen Upgrade", "tags": ["quick", "15min", "single"]},
            {"name": "Egg Fried Rice", "tags": ["quick", "20min", "single"]},
            {"name": "Avocado Toast", "tags": ["quick", "5min", "single"]},
            {"name": "Grilled Cheese Deluxe", "tags": ["quick", "10min", "single"]},
            {"name": "Instant Pot Chili", "tags": ["quick", "30min", "single"]},
            {"name": "Microwave Mac and Cheese", "tags": ["quick", "5min", "single"]},
            {"name": "Frozen Pizza Upgrade", "tags": ["quick", "15min", "single"]},
            {"name": "Scrambled Eggs", "tags": ["quick", "10min", "single"]},
            {"name": "Smoothie Bowl", "tags": ["quick", "5min", "single"]},
            {"name": "Quesadilla", "tags": ["quick", "10min", "single"]},
            {"name": "Cup of Soup", "tags": ["quick", "5min", "single"]},
            {"name": "Stir Fry from Frozen", "tags": ["quick", "15min", "single"]},
        ],
        "meal_plan_history": [
            {"date": "2026-01-22", "meal": "dinner", "recipe": "Ramen Upgrade"},
            {"date": "2026-01-25", "meal": "dinner", "recipe": "Egg Fried Rice"},
            {"date": "2026-01-28", "meal": "dinner", "recipe": "Frozen Pizza Upgrade"},
            {"date": "2026-01-31", "meal": "dinner", "recipe": "Quesadilla"},
            {"date": "2026-02-02", "meal": "dinner", "recipe": "Stir Fry from Frozen"},
        ],
        "pantry_items": [
            "instant ramen",
            "eggs",
            "sriracha",
            "soy sauce",
            "frozen dumplings",
            "bread",
            "avocado",
            "cheese",
            "microwave meals",
        ],
    },
    "gluten_free_grace": {
        "user_id": "synthetic-gluten-free-grace",
        "preferences": {
            "dietary_restrictions": ["gluten-free"],
            "cuisine_preferences": ["Italian", "American"],
            "cooking_skill": "intermediate",
            "household_size": 2,
            "has_picky_eaters": None,
            "hates_leftovers": None,
            "location": {
                "city": "Denver",
                "state_or_region": "Colorado",
                "country": "USA",
                "postal_code": "80202",
            },
        },
        "recipes": [
            {"name": "GF Pasta Carbonara", "tags": ["gluten-free", "italian", "30min"]},
            {"name": "Rice Flour Pizza", "tags": ["gluten-free", "italian", "45min"]},
            {"name": "Cauliflower Crust", "tags": ["gluten-free", "low-carb", "30min"]},
            {
                "name": "Grilled Chicken Salad",
                "tags": ["gluten-free", "healthy", "20min"],
            },
            {"name": "Rice Bowl", "tags": ["gluten-free", "asian", "25min"]},
            {"name": "GF Lasagna", "tags": ["gluten-free", "italian", "60min"]},
            {"name": "Zucchini Noodles", "tags": ["gluten-free", "healthy", "20min"]},
            {"name": "GF Pancakes", "tags": ["gluten-free", "breakfast", "20min"]},
            {"name": "Quinoa Salad", "tags": ["gluten-free", "healthy", "15min"]},
            {"name": "GF Muffins", "tags": ["gluten-free", "breakfast", "30min"]},
            {"name": "Baked Salmon", "tags": ["gluten-free", "healthy", "25min"]},
            {"name": "GF Bread", "tags": ["gluten-free", "baking", "60min"]},
            {"name": "Rice Paper Rolls", "tags": ["gluten-free", "asian", "20min"]},
            {"name": "GF Chicken Tenders", "tags": ["gluten-free", "comfort", "25min"]},
            {"name": "Polenta", "tags": ["gluten-free", "italian", "30min"]},
            {"name": "GF Brownies", "tags": ["gluten-free", "dessert", "35min"]},
            {
                "name": "Corn Tortilla Tacos",
                "tags": ["gluten-free", "mexican", "20min"],
            },
            {"name": "GF Waffles", "tags": ["gluten-free", "breakfast", "20min"]},
            {"name": "Stuffed Peppers", "tags": ["gluten-free", "comfort", "45min"]},
            {"name": "GF Fried Chicken", "tags": ["gluten-free", "comfort", "40min"]},
        ],
        "meal_plan_history": [
            {"date": "2026-01-20", "meal": "dinner", "recipe": "GF Pasta Carbonara"},
            {"date": "2026-01-21", "meal": "dinner", "recipe": "Grilled Chicken Salad"},
            {"date": "2026-01-22", "meal": "dinner", "recipe": "Rice Bowl"},
            {"date": "2026-01-23", "meal": "dinner", "recipe": "Rice Flour Pizza"},
            {"date": "2026-01-24", "meal": "dinner", "recipe": "Baked Salmon"},
            {"date": "2026-01-25", "meal": "dinner", "recipe": "Zucchini Noodles"},
            {"date": "2026-01-26", "meal": "dinner", "recipe": "GF Lasagna"},
            {"date": "2026-01-27", "meal": "dinner", "recipe": "Quinoa Salad"},
            {"date": "2026-01-28", "meal": "dinner", "recipe": "Corn Tortilla Tacos"},
            {"date": "2026-01-29", "meal": "dinner", "recipe": "Cauliflower Crust"},
            {"date": "2026-01-30", "meal": "dinner", "recipe": "Stuffed Peppers"},
            {"date": "2026-01-31", "meal": "dinner", "recipe": "GF Chicken Tenders"},
            {"date": "2026-02-01", "meal": "dinner", "recipe": "Rice Paper Rolls"},
            {"date": "2026-02-02", "meal": "dinner", "recipe": "Polenta"},
        ],
        "pantry_items": [
            "rice flour",
            "almond flour",
            "gluten-free pasta",
            "rice",
            "quinoa",
            "cornstarch",
            "xanthan gum",
            "certified GF oats",
        ],
    },
    "adventurous_alex": {
        "user_id": "synthetic-adventurous-alex",
        "preferences": {
            "dietary_restrictions": [],
            "cuisine_preferences": ["Thai", "Indian", "Japanese", "Middle Eastern"],
            "cooking_skill": "advanced",
            "household_size": 2,
            "has_picky_eaters": None,
            "hates_leftovers": None,
            "location": {
                "city": "New York",
                "state_or_region": "New York",
                "country": "USA",
                "postal_code": "10001",
            },
        },
        "recipes": [
            {"name": "Thai Green Curry", "tags": ["thai", "complex", "60min"]},
            {"name": "Homemade Ramen", "tags": ["japanese", "complex", "180min"]},
            {"name": "Butter Chicken", "tags": ["indian", "intermediate", "45min"]},
            {"name": "Pad Thai", "tags": ["thai", "intermediate", "30min"]},
            {"name": "Sushi Rolls", "tags": ["japanese", "advanced", "60min"]},
            {"name": "Moroccan Tagine", "tags": ["middle-eastern", "complex", "90min"]},
            {"name": "Korean BBQ", "tags": ["korean", "intermediate", "40min"]},
            {"name": "Pho", "tags": ["vietnamese", "complex", "120min"]},
            {
                "name": "Chicken Tikka Masala",
                "tags": ["indian", "intermediate", "50min"],
            },
            {"name": "Banh Mi", "tags": ["vietnamese", "intermediate", "30min"]},
            {"name": "Tom Yum Soup", "tags": ["thai", "intermediate", "35min"]},
            {"name": "Gyoza", "tags": ["japanese", "advanced", "60min"]},
            {"name": "Shakshuka", "tags": ["middle-eastern", "easy", "25min"]},
            {"name": "Bibimbap", "tags": ["korean", "intermediate", "45min"]},
            {"name": "Massaman Curry", "tags": ["thai", "complex", "70min"]},
            {"name": "Tandoori Chicken", "tags": ["indian", "intermediate", "60min"]},
            {"name": "Falafel", "tags": ["middle-eastern", "intermediate", "30min"]},
            {"name": "Katsu Curry", "tags": ["japanese", "intermediate", "50min"]},
            {"name": "Lamb Kofta", "tags": ["middle-eastern", "intermediate", "35min"]},
            {"name": "Green Papaya Salad", "tags": ["thai", "easy", "15min"]},
            {"name": "Okonomiyaki", "tags": ["japanese", "intermediate", "40min"]},
            {"name": "Biryani", "tags": ["indian", "complex", "90min"]},
            {"name": "Spring Rolls", "tags": ["vietnamese", "intermediate", "30min"]},
            {"name": "Miso Soup", "tags": ["japanese", "easy", "15min"]},
            {"name": "Hummus", "tags": ["middle-eastern", "easy", "20min"]},
            {"name": "Kimchi Fried Rice", "tags": ["korean", "easy", "20min"]},
            {"name": "Samosas", "tags": ["indian", "intermediate", "50min"]},
            {"name": "Teriyaki Salmon", "tags": ["japanese", "easy", "25min"]},
            {"name": "Baba Ganoush", "tags": ["middle-eastern", "easy", "30min"]},
            {"name": "Thai Basil Chicken", "tags": ["thai", "easy", "20min"]},
        ],
        "meal_plan_history": [
            {"date": "2026-01-20", "meal": "dinner", "recipe": "Thai Green Curry"},
            {"date": "2026-01-21", "meal": "dinner", "recipe": "Moroccan Tagine"},
            {"date": "2026-01-22", "meal": "dinner", "recipe": "Korean BBQ"},
            {"date": "2026-01-23", "meal": "dinner", "recipe": "Butter Chicken"},
            {"date": "2026-01-24", "meal": "dinner", "recipe": "Pad Thai"},
            {"date": "2026-01-25", "meal": "dinner", "recipe": "Sushi Rolls"},
            {"date": "2026-01-26", "meal": "dinner", "recipe": "Pho"},
            {"date": "2026-01-27", "meal": "dinner", "recipe": "Shakshuka"},
            {"date": "2026-01-28", "meal": "dinner", "recipe": "Bibimbap"},
            {"date": "2026-01-29", "meal": "dinner", "recipe": "Chicken Tikka Masala"},
            {"date": "2026-01-30", "meal": "dinner", "recipe": "Tom Yum Soup"},
            {"date": "2026-01-31", "meal": "dinner", "recipe": "Gyoza"},
            {"date": "2026-02-01", "meal": "dinner", "recipe": "Falafel"},
            {"date": "2026-02-02", "meal": "dinner", "recipe": "Katsu Curry"},
        ],
        "pantry_items": [
            "fish sauce",
            "coconut milk",
            "curry paste",
            "gochujang",
            "miso paste",
            "tahini",
            "harissa",
            "specialty spices",
            "exotic ingredients",
        ],
    },
    "routine_rita": {
        "user_id": "synthetic-routine-rita",
        "preferences": {
            "dietary_restrictions": [],
            "cuisine_preferences": ["American", "Comfort Food"],
            "cooking_skill": "intermediate",
            "household_size": 4,
            "has_picky_eaters": None,
            "hates_leftovers": None,
            "location": {
                "city": "Indianapolis",
                "state_or_region": "Indiana",
                "country": "USA",
                "postal_code": "46201",
            },
        },
        "recipes": [
            {"name": "Sunday Roast", "tags": ["comfort", "family", "120min"]},
            {"name": "Meatloaf", "tags": ["comfort", "american", "60min"]},
            {"name": "Chicken Pot Pie", "tags": ["comfort", "family", "90min"]},
            {"name": "Taco Tuesday", "tags": ["family", "mexican", "30min"]},
            {"name": "Spaghetti Wednesday", "tags": ["family", "italian", "35min"]},
            {"name": "Chicken Thursday", "tags": ["comfort", "american", "45min"]},
            {"name": "Pot Roast", "tags": ["comfort", "family", "180min"]},
            {"name": "Baked Chicken", "tags": ["comfort", "easy", "50min"]},
            {"name": "Beef Stew", "tags": ["comfort", "family", "120min"]},
            {"name": "Mashed Potatoes", "tags": ["comfort", "side", "30min"]},
            {"name": "Green Bean Casserole", "tags": ["comfort", "side", "40min"]},
            {"name": "Cornbread", "tags": ["comfort", "side", "25min"]},
            {"name": "Shepherd's Pie", "tags": ["comfort", "family", "75min"]},
            {"name": "Macaroni and Cheese", "tags": ["comfort", "family", "30min"]},
            {"name": "Roasted Turkey", "tags": ["comfort", "family", "180min"]},
        ],
        "meal_plan_history": [
            {"date": "2026-01-12", "meal": "dinner", "recipe": "Sunday Roast"},
            {"date": "2026-01-13", "meal": "dinner", "recipe": "Meatloaf"},
            {"date": "2026-01-14", "meal": "dinner", "recipe": "Taco Tuesday"},
            {"date": "2026-01-15", "meal": "dinner", "recipe": "Spaghetti Wednesday"},
            {"date": "2026-01-16", "meal": "dinner", "recipe": "Chicken Thursday"},
            {"date": "2026-01-17", "meal": "dinner", "recipe": "Pot Roast"},
            {"date": "2026-01-18", "meal": "dinner", "recipe": "Chicken Pot Pie"},
            {"date": "2026-01-19", "meal": "dinner", "recipe": "Sunday Roast"},
            {"date": "2026-01-20", "meal": "dinner", "recipe": "Meatloaf"},
            {"date": "2026-01-21", "meal": "dinner", "recipe": "Taco Tuesday"},
            {"date": "2026-01-22", "meal": "dinner", "recipe": "Spaghetti Wednesday"},
            {"date": "2026-01-23", "meal": "dinner", "recipe": "Chicken Thursday"},
            {"date": "2026-01-24", "meal": "dinner", "recipe": "Pot Roast"},
            {"date": "2026-01-25", "meal": "dinner", "recipe": "Beef Stew"},
            {"date": "2026-01-26", "meal": "dinner", "recipe": "Sunday Roast"},
            {"date": "2026-01-27", "meal": "dinner", "recipe": "Meatloaf"},
            {"date": "2026-01-28", "meal": "dinner", "recipe": "Taco Tuesday"},
            {"date": "2026-01-29", "meal": "dinner", "recipe": "Spaghetti Wednesday"},
            {"date": "2026-01-30", "meal": "dinner", "recipe": "Chicken Thursday"},
            {"date": "2026-01-31", "meal": "dinner", "recipe": "Shepherd's Pie"},
            {"date": "2026-02-01", "meal": "dinner", "recipe": "Chicken Pot Pie"},
            {"date": "2026-02-02", "meal": "dinner", "recipe": "Sunday Roast"},
        ],
        "pantry_items": [
            "ground beef",
            "chicken",
            "potatoes",
            "carrots",
            "onions",
            "pasta",
            "canned tomatoes",
            "cream of mushroom soup",
            "breadcrumbs",
        ],
    },
    "fitness_frank": {
        "user_id": "synthetic-fitness-frank",
        "preferences": {
            "dietary_restrictions": ["high-protein"],
            "cuisine_preferences": ["American", "Mediterranean"],
            "cooking_skill": "intermediate",
            "household_size": 1,
            "has_picky_eaters": None,
            "hates_leftovers": None,
            "location": {
                "city": "Austin",
                "state_or_region": "Texas",
                "country": "USA",
                "postal_code": "78701",
            },
        },
        "recipes": [
            {
                "name": "Protein Pancakes",
                "tags": ["high-protein", "breakfast", "15min"],
            },
            {
                "name": "Grilled Chicken Meal Prep",
                "tags": ["high-protein", "batch", "45min"],
            },
            {"name": "Greek Yogurt Bowl", "tags": ["high-protein", "quick", "5min"]},
            {
                "name": "Salmon and Broccoli",
                "tags": ["high-protein", "healthy", "25min"],
            },
            {"name": "Protein Shake", "tags": ["high-protein", "quick", "5min"]},
            {
                "name": "Egg White Omelette",
                "tags": ["high-protein", "breakfast", "15min"],
            },
            {"name": "Tuna Salad", "tags": ["high-protein", "quick", "10min"]},
            {
                "name": "Chicken Breast and Rice",
                "tags": ["high-protein", "meal-prep", "40min"],
            },
            {"name": "Cottage Cheese Bowl", "tags": ["high-protein", "quick", "5min"]},
            {"name": "Grilled Steak", "tags": ["high-protein", "dinner", "30min"]},
            {"name": "Protein Bars", "tags": ["high-protein", "snack", "30min"]},
            {
                "name": "Turkey Meatballs",
                "tags": ["high-protein", "meal-prep", "35min"],
            },
            {"name": "Quinoa Power Bowl", "tags": ["high-protein", "healthy", "30min"]},
            {"name": "Beef Jerky", "tags": ["high-protein", "snack", "180min"]},
            {"name": "Shrimp Stir Fry", "tags": ["high-protein", "quick", "20min"]},
            {"name": "Protein Muffins", "tags": ["high-protein", "breakfast", "30min"]},
            {"name": "Chicken Fajitas", "tags": ["high-protein", "dinner", "25min"]},
            {"name": "Tuna Poke Bowl", "tags": ["high-protein", "healthy", "15min"]},
            {"name": "Baked Tilapia", "tags": ["high-protein", "healthy", "20min"]},
            {"name": "Egg Bites", "tags": ["high-protein", "breakfast", "25min"]},
            {"name": "Turkey Chili", "tags": ["high-protein", "meal-prep", "50min"]},
            {
                "name": "Grilled Chicken Salad",
                "tags": ["high-protein", "healthy", "20min"],
            },
            {
                "name": "Protein Smoothie Bowl",
                "tags": ["high-protein", "breakfast", "10min"],
            },
            {"name": "Baked Cod", "tags": ["high-protein", "healthy", "25min"]},
            {
                "name": "Chicken Lettuce Wraps",
                "tags": ["high-protein", "low-carb", "15min"],
            },
        ],
        "meal_plan_history": [
            {"date": "2026-01-20", "meal": "breakfast", "recipe": "Protein Pancakes"},
            {
                "date": "2026-01-20",
                "meal": "lunch",
                "recipe": "Grilled Chicken Meal Prep",
            },
            {"date": "2026-01-20", "meal": "dinner", "recipe": "Salmon and Broccoli"},
            {"date": "2026-01-21", "meal": "breakfast", "recipe": "Egg White Omelette"},
            {
                "date": "2026-01-21",
                "meal": "lunch",
                "recipe": "Grilled Chicken Meal Prep",
            },
            {"date": "2026-01-21", "meal": "dinner", "recipe": "Grilled Steak"},
            {"date": "2026-01-22", "meal": "breakfast", "recipe": "Greek Yogurt Bowl"},
            {"date": "2026-01-22", "meal": "lunch", "recipe": "Tuna Salad"},
            {
                "date": "2026-01-22",
                "meal": "dinner",
                "recipe": "Chicken Breast and Rice",
            },
            {"date": "2026-01-23", "meal": "breakfast", "recipe": "Protein Shake"},
            {
                "date": "2026-01-23",
                "meal": "lunch",
                "recipe": "Grilled Chicken Meal Prep",
            },
            {"date": "2026-01-23", "meal": "dinner", "recipe": "Turkey Meatballs"},
            {"date": "2026-01-24", "meal": "breakfast", "recipe": "Egg Bites"},
            {"date": "2026-01-24", "meal": "lunch", "recipe": "Quinoa Power Bowl"},
            {"date": "2026-01-24", "meal": "dinner", "recipe": "Shrimp Stir Fry"},
            {"date": "2026-01-25", "meal": "breakfast", "recipe": "Protein Pancakes"},
            {"date": "2026-01-25", "meal": "lunch", "recipe": "Grilled Chicken Salad"},
            {"date": "2026-01-25", "meal": "dinner", "recipe": "Baked Cod"},
            {
                "date": "2026-01-26",
                "meal": "breakfast",
                "recipe": "Protein Smoothie Bowl",
            },
            {"date": "2026-01-26", "meal": "lunch", "recipe": "Tuna Poke Bowl"},
            {"date": "2026-01-26", "meal": "dinner", "recipe": "Chicken Fajitas"},
            {"date": "2026-01-27", "meal": "breakfast", "recipe": "Egg White Omelette"},
            {
                "date": "2026-01-27",
                "meal": "lunch",
                "recipe": "Grilled Chicken Meal Prep",
            },
            {"date": "2026-01-27", "meal": "dinner", "recipe": "Salmon and Broccoli"},
        ],
        "pantry_items": [
            "protein powder",
            "chicken breast",
            "eggs",
            "greek yogurt",
            "tuna",
            "salmon",
            "cottage cheese",
            "quinoa",
            "brown rice",
            "broccoli",
        ],
    },
    "dairy_free_dana": {
        "user_id": "synthetic-dairy-free-dana",
        "preferences": {
            "dietary_restrictions": ["dairy-free", "vegetarian"],
            "cuisine_preferences": ["Asian", "Mediterranean"],
            "cooking_skill": "intermediate",
            "household_size": 2,
            "has_picky_eaters": None,
            "hates_leftovers": None,
            "location": {
                "city": "Portland",
                "state_or_region": "Oregon",
                "country": "USA",
                "postal_code": "97201",
            },
        },
        "recipes": [
            {
                "name": "Coconut Curry",
                "tags": ["dairy-free", "vegetarian", "thai", "30min"],
            },
            {
                "name": "Vegan Mac and Cheese",
                "tags": ["dairy-free", "vegetarian", "comfort", "25min"],
            },
            {
                "name": "Cashew Cream Pasta",
                "tags": ["dairy-free", "vegetarian", "italian", "30min"],
            },
            {
                "name": "Stir Fry with Tofu",
                "tags": ["dairy-free", "vegetarian", "asian", "20min"],
            },
            {
                "name": "Hummus Bowl",
                "tags": ["dairy-free", "vegetarian", "mediterranean", "15min"],
            },
            {
                "name": "Vegan Pizza",
                "tags": ["dairy-free", "vegetarian", "italian", "40min"],
            },
            {
                "name": "Tofu Scramble",
                "tags": ["dairy-free", "vegetarian", "breakfast", "15min"],
            },
            {
                "name": "Lentil Dal",
                "tags": ["dairy-free", "vegetarian", "indian", "35min"],
            },
            {
                "name": "Peanut Noodles",
                "tags": ["dairy-free", "vegetarian", "asian", "20min"],
            },
            {
                "name": "Roasted Vegetable Bowl",
                "tags": ["dairy-free", "vegetarian", "healthy", "30min"],
            },
            {
                "name": "Vegan Tacos",
                "tags": ["dairy-free", "vegetarian", "mexican", "25min"],
            },
            {
                "name": "Coconut Milk Smoothie",
                "tags": ["dairy-free", "vegetarian", "quick", "5min"],
            },
            {
                "name": "Vegan Burrito",
                "tags": ["dairy-free", "vegetarian", "mexican", "20min"],
            },
            {
                "name": "Tahini Dressing Salad",
                "tags": ["dairy-free", "vegetarian", "healthy", "15min"],
            },
            {
                "name": "Vegan Chili",
                "tags": ["dairy-free", "vegetarian", "comfort", "45min"],
            },
            {
                "name": "Almond Milk Pancakes",
                "tags": ["dairy-free", "vegetarian", "breakfast", "20min"],
            },
            {
                "name": "Tempeh Stir Fry",
                "tags": ["dairy-free", "vegetarian", "asian", "25min"],
            },
            {
                "name": "Vegan Pad Thai",
                "tags": ["dairy-free", "vegetarian", "thai", "30min"],
            },
            {
                "name": "Coconut Yogurt Parfait",
                "tags": ["dairy-free", "vegetarian", "breakfast", "10min"],
            },
            {
                "name": "Vegan Lasagna",
                "tags": ["dairy-free", "vegetarian", "italian", "60min"],
            },
        ],
        "meal_plan_history": [
            {"date": "2026-01-20", "meal": "dinner", "recipe": "Coconut Curry"},
            {"date": "2026-01-21", "meal": "dinner", "recipe": "Vegan Mac and Cheese"},
            {"date": "2026-01-22", "meal": "dinner", "recipe": "Stir Fry with Tofu"},
            {"date": "2026-01-23", "meal": "dinner", "recipe": "Cashew Cream Pasta"},
            {"date": "2026-01-24", "meal": "dinner", "recipe": "Hummus Bowl"},
            {"date": "2026-01-25", "meal": "dinner", "recipe": "Vegan Pizza"},
            {"date": "2026-01-26", "meal": "dinner", "recipe": "Lentil Dal"},
            {"date": "2026-01-27", "meal": "dinner", "recipe": "Peanut Noodles"},
            {"date": "2026-01-28", "meal": "dinner", "recipe": "Vegan Tacos"},
            {
                "date": "2026-01-29",
                "meal": "dinner",
                "recipe": "Roasted Vegetable Bowl",
            },
            {"date": "2026-01-30", "meal": "dinner", "recipe": "Vegan Burrito"},
            {"date": "2026-01-31", "meal": "dinner", "recipe": "Tempeh Stir Fry"},
            {"date": "2026-02-01", "meal": "dinner", "recipe": "Vegan Pad Thai"},
            {"date": "2026-02-02", "meal": "dinner", "recipe": "Vegan Chili"},
        ],
        "pantry_items": [
            "coconut milk",
            "cashews",
            "nutritional yeast",
            "oat milk",
            "vegan butter",
            "tofu",
            "tempeh",
            "tahini",
            "almond milk",
            "coconut oil",
        ],
    },
}

# Target sample counts per persona (total ~1000)
SAMPLE_TARGETS: dict[str, int] = {
    "veggie_val": 150,  # Good variety, common use case
    "family_fiona": 200,  # Most common demographic
    "solo_sam": 150,  # Growing segment
    "gluten_free_grace": 100,  # Important edge case
    "adventurous_alex": 100,  # Exploratory queries
    "routine_rita": 150,  # Heavy history usage
    "fitness_frank": 75,  # Niche but important
    "dairy_free_dana": 75,  # Compound restrictions
}


def get_persona(persona_name: str) -> PersonaProfile:
    """Get persona profile by name.

    Args:
        persona_name: Name of the persona (e.g., "veggie_val")

    Returns:
        PersonaProfile dictionary

    Raises:
        KeyError: If persona name is not found
    """
    return PERSONAS[persona_name]


def list_persona_names() -> list[str]:
    """Get all available persona names.

    Returns:
        List of persona identifier strings
    """
    return list(PERSONAS.keys())


def get_sample_target(persona_name: str) -> int:
    """Get target number of samples to generate for a persona.

    Args:
        persona_name: Name of the persona

    Returns:
        Target sample count

    Raises:
        KeyError: If persona name is not found
    """
    return SAMPLE_TARGETS[persona_name]
