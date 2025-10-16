"""
Centralized business data constants for Owl Internet.
Single source of truth for all business information.
"""

# Company Information
COMPANY_INFO = {
    "name": "Owl Internet",
    "founded": "2018",
    "service_areas": "Nationwide fiber and cable internet",
    "phone": "1-800-OWL-HELP",
    "email": "help@owlinternet.com",
    "website": "owlinternet.com",
    "hours": "24/7 customer support",
}

# Internet Plans
INTERNET_PLANS = {
    "100": {
        "name": "Basic",
        "speed": "one hundred megabits per second",
        "price": "thirty-nine dollars and ninety-nine cents per month",
        "description": "Perfect for browsing and streaming",
    },
    "300": {
        "name": "Standard",
        "speed": "three hundred megabits per second",
        "price": "fifty-nine dollars and ninety-nine cents per month",
        "description": "Great for families and remote work",
    },
    "500": {
        "name": "Advanced",
        "speed": "five hundred megabits per second",
        "price": "seventy-four dollars and ninety-nine cents per month",
        "description": "High-speed for power users",
    },
    "1000": {
        "name": "Premium",
        "speed": "one thousand megabits per second",
        "price": "eighty-nine dollars and ninety-nine cents per month",
        "description": "Ultra-fast for heavy usage and gaming",
    },
    "1gig": {
        "name": "Premium",
        "speed": "one thousand megabits per second",
        "price": "eighty-nine dollars and ninety-nine cents per month",
        "description": "Ultra-fast for heavy usage and gaming",
    },
    "gigabit": {
        "name": "Premium",
        "speed": "one thousand megabits per second",
        "price": "eighty-nine dollars and ninety-nine cents per month",
        "description": "Ultra-fast for heavy usage and gaming",
    },
}

# Router Information
ROUTER_MODELS = {
    "OWL-R2021": {
        "max_speed": "three hundred megabits per second",
        "wifi_standard": "WiFi 5",
        "upgrade_needed": "For speeds above three hundred megabits per second, upgrade to X5 router recommended",
        "upgrade_cost": "one hundred dollars (or twenty-five dollars for loyal customers)",
    },
    "OWL-R2019": {
        "max_speed": "one hundred fifty megabits per second",
        "wifi_standard": "WiFi 5",
        "upgrade_needed": "Router is limiting your plan speeds. X5 upgrade strongly recommended",
        "upgrade_cost": "one hundred dollars (or twenty-five dollars for loyal customers)",
    },
    "OWL-X5": {
        "max_speed": "one thousand plus megabits per second",
        "wifi_standard": "WiFi 6",
        "upgrade_needed": "Latest model - no upgrade needed",
        "upgrade_cost": "Not applicable",
    },
}

# Loyalty Tiers
LOYALTY_TIERS = {"new": "0-1 years", "loyal": "2-4 years", "premium": "5+ years"}

# Promotions and Discounts
PROMOTIONS = {
    "autopay_discount": "fifteen dollars per month off any plan upgrade",
    "loyalty_discount_2yr": "ten percent off monthly rate",
    "loyalty_discount_5yr": "twenty percent off monthly rate",
    "retention_offer": "fifty percent off first six months",
}


# # Dynamic Customer Phone Mapping
# def get_customer_phone_mapping():
#     """Get customer phone mapping from ProfileManager."""
#     mapping = {}
#     try:
#         for profile in profile_manager.get_demo_customers():
#             # Create mapping from name variations to phone
#             name_key = profile.name.lower().replace(' ', '_')
#             mapping[name_key] = profile.phone
#
#             # Also map by first name
#             first_name = profile.name.split()[0].lower()
#             mapping[first_name] = profile.phone
#     except Exception as e:
#         # Fallback to prevent import errors
#         mapping = {"ashley_chen": "+14085551234", "demo_customer": "+12062271647"}
#     return mapping
#
#
# # Dynamic mapping instead of hardcoded
# CUSTOMER_PHONE_MAPPING = get_customer_phone_mapping()

# Standard Test Phone Numbers (legacy support)
TEST_PHONE_NUMBERS = {"generic_test": "+15551234567"}
