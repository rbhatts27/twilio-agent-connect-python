"""
Centralized business data constants for All My Sons Moving & Storage.
Single source of truth for all moving industry business information.

This data powers the AI agent's domain knowledge for:
- Quote calculations
- Furniture/item identification
- Pricing matrices
- Special handling requirements
"""

# Company Information
COMPANY_INFO = {
    "name": "All My Sons Moving & Storage",
    "tagline": "Your Moving Family Since 1990",
    "phone": "1-800-ALL-SONS",
    "email": "quotes@allmysons.com",
    "website": "allmysons.com",
    "hours": "7 AM - 9 PM, 7 days a week",
    "founded": "1990",
    "coverage": "Nationwide - 90+ locations across the US",
}

# Furniture Types with weights and handling requirements
FURNITURE_TYPES = {
    "sofa": {
        "category": "living_room",
        "avg_weight_lbs": 200,
        "cubic_feet": 60,
        "handling": "standard",
        "description": "Standard 3-seat sofa",
    },
    "sectional_sofa": {
        "category": "living_room",
        "avg_weight_lbs": 350,
        "cubic_feet": 100,
        "handling": "standard",
        "description": "L-shaped or U-shaped sectional",
    },
    "armchair": {
        "category": "living_room",
        "avg_weight_lbs": 75,
        "cubic_feet": 25,
        "handling": "standard",
        "description": "Single armchair or recliner",
    },
    "coffee_table": {
        "category": "living_room",
        "avg_weight_lbs": 50,
        "cubic_feet": 15,
        "handling": "standard",
        "description": "Standard coffee table",
    },
    "entertainment_center": {
        "category": "living_room",
        "avg_weight_lbs": 200,
        "cubic_feet": 50,
        "handling": "fragile",
        "description": "TV stand or entertainment unit",
    },
    "bookshelf": {
        "category": "living_room",
        "avg_weight_lbs": 100,
        "cubic_feet": 30,
        "handling": "standard",
        "description": "Tall bookshelf unit",
    },
    "dining_table": {
        "category": "dining",
        "avg_weight_lbs": 150,
        "cubic_feet": 40,
        "handling": "standard",
        "description": "6-8 person dining table",
    },
    "dining_chair": {
        "category": "dining",
        "avg_weight_lbs": 20,
        "cubic_feet": 8,
        "handling": "standard",
        "description": "Single dining chair",
    },
    "china_cabinet": {
        "category": "dining",
        "avg_weight_lbs": 300,
        "cubic_feet": 60,
        "handling": "fragile",
        "description": "Glass-front display cabinet",
    },
    "king_bed": {
        "category": "bedroom",
        "avg_weight_lbs": 200,
        "cubic_feet": 80,
        "handling": "standard",
        "description": "King size bed frame + mattress",
    },
    "queen_bed": {
        "category": "bedroom",
        "avg_weight_lbs": 150,
        "cubic_feet": 60,
        "handling": "standard",
        "description": "Queen size bed frame + mattress",
    },
    "dresser": {
        "category": "bedroom",
        "avg_weight_lbs": 150,
        "cubic_feet": 35,
        "handling": "standard",
        "description": "6-drawer dresser",
    },
    "nightstand": {
        "category": "bedroom",
        "avg_weight_lbs": 40,
        "cubic_feet": 10,
        "handling": "standard",
        "description": "Bedside table",
    },
    "desk": {
        "category": "office",
        "avg_weight_lbs": 100,
        "cubic_feet": 30,
        "handling": "standard",
        "description": "Home office desk",
    },
    "office_chair": {
        "category": "office",
        "avg_weight_lbs": 40,
        "cubic_feet": 15,
        "handling": "standard",
        "description": "Ergonomic office chair",
    },
    "filing_cabinet": {
        "category": "office",
        "avg_weight_lbs": 80,
        "cubic_feet": 15,
        "handling": "standard",
        "description": "2-4 drawer filing cabinet",
    },
    "refrigerator": {
        "category": "appliance",
        "avg_weight_lbs": 300,
        "cubic_feet": 30,
        "handling": "appliance",
        "description": "Standard refrigerator",
    },
    "washer": {
        "category": "appliance",
        "avg_weight_lbs": 180,
        "cubic_feet": 20,
        "handling": "appliance",
        "description": "Washing machine",
    },
    "dryer": {
        "category": "appliance",
        "avg_weight_lbs": 150,
        "cubic_feet": 20,
        "handling": "appliance",
        "description": "Clothes dryer",
    },
}

# Special items requiring extra care and pricing
SPECIAL_ITEMS = {
    "baby_grand_piano": {
        "category": "musical",
        "avg_weight_lbs": 600,
        "cubic_feet": 80,
        "handling": "piano_specialty",
        "base_fee": 800,
        "description": "5-6 foot baby grand piano",
        "requirements": ["piano board", "piano straps", "4-person crew", "climate control"],
        "insurance_value_typical": 15000,
    },
    "grand_piano": {
        "category": "musical",
        "avg_weight_lbs": 900,
        "cubic_feet": 120,
        "handling": "piano_specialty",
        "base_fee": 1200,
        "description": "7+ foot concert grand piano",
        "requirements": ["piano board", "piano straps", "6-person crew", "climate control"],
        "insurance_value_typical": 50000,
    },
    "upright_piano": {
        "category": "musical",
        "avg_weight_lbs": 400,
        "cubic_feet": 40,
        "handling": "piano_specialty",
        "base_fee": 400,
        "description": "Standard upright piano",
        "requirements": ["piano straps", "3-person crew"],
        "insurance_value_typical": 5000,
    },
    "antique_furniture": {
        "category": "antique",
        "avg_weight_lbs": 150,
        "cubic_feet": 40,
        "handling": "white_glove",
        "base_fee": 200,
        "description": "Antique furniture piece (cabinet, armoire, etc.)",
        "requirements": ["furniture pads", "custom crating available", "climate control"],
        "insurance_value_typical": 5000,
    },
    "antique_cabinet": {
        "category": "antique",
        "avg_weight_lbs": 200,
        "cubic_feet": 50,
        "handling": "white_glove",
        "base_fee": 300,
        "description": "Antique display cabinet or hutch",
        "requirements": ["furniture pads", "custom crating", "climate control"],
        "insurance_value_typical": 8000,
    },
    "grandfather_clock": {
        "category": "antique",
        "avg_weight_lbs": 200,
        "cubic_feet": 25,
        "handling": "white_glove",
        "base_fee": 350,
        "description": "Tall case grandfather clock",
        "requirements": ["clock specialist", "custom crating", "separate movement transport"],
        "insurance_value_typical": 10000,
    },
    "pool_table": {
        "category": "specialty",
        "avg_weight_lbs": 800,
        "cubic_feet": 100,
        "handling": "disassembly_required",
        "base_fee": 600,
        "description": "Full-size pool/billiard table",
        "requirements": ["disassembly", "slate handling", "reassembly", "re-felting optional"],
        "insurance_value_typical": 3000,
    },
    "hot_tub": {
        "category": "specialty",
        "avg_weight_lbs": 800,
        "cubic_feet": 150,
        "handling": "crane_required",
        "base_fee": 1000,
        "description": "Outdoor spa/hot tub",
        "requirements": ["crane rental", "electrical disconnect", "4-person crew"],
        "insurance_value_typical": 8000,
    },
    "safe": {
        "category": "specialty",
        "avg_weight_lbs": 500,
        "cubic_feet": 20,
        "handling": "heavy_specialty",
        "base_fee": 400,
        "description": "Gun safe or home safe",
        "requirements": ["heavy equipment", "floor protection", "3-person crew"],
        "insurance_value_typical": 2000,
    },
    "artwork_large": {
        "category": "art",
        "avg_weight_lbs": 50,
        "cubic_feet": 30,
        "handling": "white_glove",
        "base_fee": 150,
        "description": "Large framed artwork or mirror",
        "requirements": ["art crate", "climate control", "white glove handling"],
        "insurance_value_typical": 5000,
    },
    "wine_collection": {
        "category": "specialty",
        "avg_weight_lbs": 100,  # per case
        "cubic_feet": 5,  # per case
        "handling": "climate_controlled",
        "base_fee": 50,  # per case
        "description": "Wine collection (per case of 12)",
        "requirements": ["climate-controlled truck", "vibration dampening"],
        "insurance_value_typical": 500,  # per case
    },
}

# Distance-based pricing matrix (per mile rates)
PRICING_MATRIX = {
    "local": {  # Under 50 miles
        "per_mile": 0,  # Flat rate for local
        "base_rate_per_sqft": 3.50,
        "min_charge": 400,
        "labor_rate_per_hour": 150,  # Per mover
        "truck_fee": 0,  # Included
    },
    "regional": {  # 50-500 miles
        "per_mile": 1.50,
        "base_rate_per_sqft": 2.75,
        "min_charge": 1500,
        "labor_rate_per_hour": 0,  # Included in per-mile
        "truck_fee": 200,
    },
    "long_distance": {  # 500-1500 miles
        "per_mile": 1.25,
        "base_rate_per_sqft": 2.50,
        "min_charge": 3000,
        "labor_rate_per_hour": 0,  # Included
        "truck_fee": 400,
    },
    "cross_country": {  # Over 1500 miles
        "per_mile": 1.00,
        "base_rate_per_sqft": 2.25,
        "min_charge": 5000,
        "labor_rate_per_hour": 0,  # Included
        "truck_fee": 600,
    },
}

# Common city pairs with approximate distances
CITY_DISTANCES = {
    ("Phoenix, AZ", "Austin, TX"): 870,
    ("Phoenix, AZ", "Los Angeles, CA"): 370,
    ("Phoenix, AZ", "Denver, CO"): 600,
    ("Phoenix, AZ", "Dallas, TX"): 870,
    ("Los Angeles, CA", "San Francisco, CA"): 380,
    ("Los Angeles, CA", "Seattle, WA"): 1140,
    ("Los Angeles, CA", "Las Vegas, NV"): 270,
    ("New York, NY", "Boston, MA"): 215,
    ("New York, NY", "Philadelphia, PA"): 95,
    ("New York, NY", "Washington, DC"): 225,
    ("New York, NY", "Miami, FL"): 1280,
    ("Chicago, IL", "Detroit, MI"): 280,
    ("Chicago, IL", "Minneapolis, MN"): 410,
    ("Dallas, TX", "Houston, TX"): 240,
    ("Dallas, TX", "Austin, TX"): 195,
    ("Seattle, WA", "Portland, OR"): 175,
    ("Atlanta, GA", "Charlotte, NC"): 245,
    ("Atlanta, GA", "Nashville, TN"): 250,
    ("Denver, CO", "Salt Lake City, UT"): 525,
    ("Miami, FL", "Orlando, FL"): 235,
}

# Packing service options
PACKING_SERVICES = {
    "full_pack": {
        "name": "Full Packing Service",
        "description": "We pack everything - all boxes, wrapping, and materials included",
        "rate_per_sqft": 1.50,
        "min_charge": 300,
    },
    "partial_pack": {
        "name": "Partial Packing",
        "description": "We pack fragile items and kitchen - you pack the rest",
        "rate_per_sqft": 0.75,
        "min_charge": 150,
    },
    "fragile_only": {
        "name": "Fragile Items Only",
        "description": "We handle dishes, artwork, electronics, and breakables",
        "rate_per_sqft": 0.40,
        "min_charge": 100,
    },
    "self_pack": {
        "name": "Self-Pack",
        "description": "You pack everything - we just move",
        "rate_per_sqft": 0,
        "min_charge": 0,
    },
}

# Insurance options
INSURANCE_OPTIONS = {
    "basic": {
        "name": "Basic Coverage (Included)",
        "description": "Standard carrier liability - $0.60 per pound per item",
        "rate": 0,  # Included
        "coverage_type": "per_pound",
        "coverage_amount": 0.60,
        "example": "A 50 lb dresser would be covered for $30 max",
    },
    "full_value": {
        "name": "Full Value Protection",
        "description": "Full replacement value or repair - $1,000 minimum",
        "rate_per_thousand": 12,  # $12 per $1,000 of declared value
        "coverage_type": "replacement_value",
        "min_declared_value": 10000,
        "deductible": 250,
        "example": "Declare $50,000 total value = $600 for full protection",
    },
    "high_value": {
        "name": "High-Value Items Coverage",
        "description": "Special coverage for items over $5,000 each (pianos, antiques, art)",
        "rate_per_thousand": 18,  # Higher rate for high-value items
        "coverage_type": "scheduled_items",
        "requires_appraisal": True,
        "example": "Your $15,000 piano would cost $270 to fully insure",
    },
}

# Storage options
STORAGE_OPTIONS = {
    "short_term": {
        "name": "Short-Term Storage",
        "description": "1-4 weeks - perfect for move-in date gaps",
        "rate_per_sqft_month": 2.50,
        "min_charge_month": 200,
        "features": ["Climate controlled", "24/7 security", "Free first month with long-distance move"],
    },
    "long_term": {
        "name": "Long-Term Storage",
        "description": "1+ months - discounted rates for extended storage",
        "rate_per_sqft_month": 1.75,
        "min_charge_month": 150,
        "features": ["Climate controlled", "24/7 security", "Monthly access visits included"],
    },
    "vault_storage": {
        "name": "Vault Storage",
        "description": "Your items stay packed in our vault containers",
        "rate_per_vault_month": 250,
        "vault_size_sqft": 175,  # Equivalent to 5x7 storage unit
        "features": ["Items stay wrapped", "No handling between moves", "Perfect for cross-country"],
    },
}

# Move crews and their specialties
MOVE_CREWS = {
    "standard": {
        "size": 2,
        "specialty": "Standard residential moves",
        "can_handle": ["standard", "fragile"],
        "hourly_rate": 150,
    },
    "large_home": {
        "size": 3,
        "specialty": "Large homes and heavy items",
        "can_handle": ["standard", "fragile", "appliance"],
        "hourly_rate": 200,
    },
    "specialty": {
        "size": 4,
        "specialty": "Pianos, antiques, and high-value items",
        "can_handle": ["standard", "fragile", "appliance", "piano_specialty", "white_glove"],
        "hourly_rate": 275,
    },
    "commercial": {
        "size": 4,
        "specialty": "Office and commercial moves",
        "can_handle": ["standard", "fragile", "office", "heavy_specialty"],
        "hourly_rate": 250,
    },
}

# Home size estimates (for quick quotes)
HOME_SIZE_ESTIMATES = {
    "studio": {"sqft_range": (300, 600), "typical_weight_lbs": 2000, "truck_size": "small"},
    "1br": {"sqft_range": (600, 900), "typical_weight_lbs": 3500, "truck_size": "small"},
    "2br": {"sqft_range": (900, 1400), "typical_weight_lbs": 5000, "truck_size": "medium"},
    "3br": {"sqft_range": (1400, 2200), "typical_weight_lbs": 8000, "truck_size": "large"},
    "4br": {"sqft_range": (2200, 3000), "typical_weight_lbs": 11000, "truck_size": "xlarge"},
    "5br+": {"sqft_range": (3000, 5000), "typical_weight_lbs": 15000, "truck_size": "semi"},
}

# Truck sizes
TRUCK_SIZES = {
    "small": {"length_ft": 12, "capacity_sqft": 450, "description": "Studio to 1BR"},
    "medium": {"length_ft": 17, "capacity_sqft": 850, "description": "1-2 BR apartment"},
    "large": {"length_ft": 22, "capacity_sqft": 1200, "description": "2-3 BR home"},
    "xlarge": {"length_ft": 26, "capacity_sqft": 1700, "description": "3-4 BR home"},
    "semi": {"length_ft": 53, "capacity_sqft": 3000, "description": "Large home or multiple units"},
}


def get_distance(origin: str, destination: str) -> int:
    """
    Get distance between two cities.
    Returns approximate mileage or estimates based on state distance.

    Args:
        origin: Origin city, state (e.g., "Phoenix, AZ")
        destination: Destination city, state (e.g., "Austin, TX")

    Returns:
        Distance in miles (approximate)
    """
    # Check direct lookup
    key = (origin, destination)
    if key in CITY_DISTANCES:
        return CITY_DISTANCES[key]

    # Check reverse
    key_reverse = (destination, origin)
    if key_reverse in CITY_DISTANCES:
        return CITY_DISTANCES[key_reverse]

    # Estimate based on common distances (fallback)
    # Average cross-country move is ~1000-1500 miles
    return 800  # Default estimate


def get_pricing_tier(distance: int) -> str:
    """
    Get pricing tier based on distance.

    Args:
        distance: Distance in miles

    Returns:
        Pricing tier key
    """
    if distance < 50:
        return "local"
    elif distance < 500:
        return "regional"
    elif distance < 1500:
        return "long_distance"
    else:
        return "cross_country"
