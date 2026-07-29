# Pre-filter guardrails — emergency and scope detection.
import re
from app.config import EMERGENCY_RESPONSE

EMERGENCY_PATTERNS = [
    r'\bchest\s+pain\b', r'\bheart\s+attack\b', r'\bcardiac\s+arrest\b',
    r'\bcan\s*(?:no)?t\s+breathe?\b', r'\bdifficulty\s+breathing\b', r'\bshortness\s+of\s+breath\b',
    r'\bchoking\b', r'\bsuffocating\b', r'\bsevere\s+bleeding\b', r'\buncontrolled\s+bleeding\b',
    r'\bbleeding\s+(?:heavily|profusely|won\'?t\s+stop)\b',
    r'\b(?:having|think|symptom|sign).*\bstroke\b|\bstroke\b.*\b(?:symptom|sign|having|think)\b',
    r'\bseizure\b', r'\bunconscious\b', r'\bpassed?\s+out\b', r'\bfaint(?:ed|ing)\b',
    r'\bsuicid(?:e|al)\b', r'\bkill\s+(?:my)?self\b', r'\bwant\s+to\s+die\b', r'\bself[- ]harm\b',
    r'\bend\s+(?:my|it\s+all|this)\s+life\b', r'\boverdos(?:e|ed|ing)\b', r'\bpoisoned?\b',
    r'\bswallowed\s+(?:pills?|bleach|chemicals?)\b', r'\banaphyla(?:xis|ctic)\b',
    r'\bthroat\s+(?:is\s+)?(?:closing|swelling)\b', r'\bcan\s*(?:no)?t\s+swallow\b',
    r'\bsevere\s+burn\b', r'\bgunshot\b', r'\bstab(?:bed|bing)\b',
]
_EMERGENCY_RE = [re.compile(p, re.IGNORECASE) for p in EMERGENCY_PATTERNS]

HEALTH_TERMS = [
    "health", "medical", "symptom", "symptoms", "disease", "diseases", "condition", "conditions",
    "pain", "fever", "cold", "flu", "headache", "headaches", "blood", "pressure", "heart",
    "skin", "rash", "burn", "burns", "wound", "wounds", "cough", "coughing", "virus",
    "bacteria", "infection", "infections", "diet", "nutrition", "exercise", "sleep", "stress",
    "mental", "anxiety", "depression", "cancer", "diabetes", "asthma", "allergy", "allergies",
    "doctor", "hospital", "medicine", "medication", "pill", "pills", "treatment", "cure",
    "first aid", "vaccine", "vaccination", "body", "stomach", "chest", "throat", "lung",
    "lungs", "kidney", "kidneys", "liver", "brain", "weight", "calorie", "calories",
    "hydration", "dehydration", "hypertension", "stroke", "seizure", "injury", "injuries",
    "sick", "illness", "wellness", "fitness", "vitamin", "vitamins", "dosage", "dose",
]

NON_HEALTH_PATTERNS = [
    r'\b(?:what\'?s?|tell|show|current|today\'?s?)\s+(?:the\s+)?(?:date|time|day|year|month)\b',
    r'\btoday\'?s?\s+date\b',
    r'\b(?:prime\s+minister|president|governor|chancellor|politician|parliament|election|political|minister|king|queen|senator|congress)\b',
    r'\bwho\s+is\s+(?:the\s+)?(?:current\s+)?(?:pm|leader|head|ceo|founder|king|queen|president|prime\s+minister)\b',
    r'\b(?:capital|population|currency|language|flag)\s+of\b',
    r'\b(?:how\s+tall|how\s+high|how\s+deep|how\s+far)\s+is\b',
    r'\b(?:highest\s+mountain|largest\s+city|longest\s+river)\b',
    r'\b(?:tell\s+me\s+a?\s*joke|who\s+won|movie|actor|actress|singer|song|album|game|match|sport)\b',
    r'\b(?:recipe|cook(?:ing)?|baking|cake|dish)\b(?!.*(?:diet|nutrition|health))',
    r'\b(?:stock|invest|financ|money|crypto|bitcoin|trading)\b',
    r'\b(?:math|calculus|algebra|equation|pythagorean)\b',
    r'\b\d+\s*[\+\-\*\/\=]\s*\d+\b',
    r'\b(?:code|program|software|javascript|python|css|html|react|java|c\+\+)\b(?!.*(?:health|medical))',
]
_NON_HEALTH_RE = [re.compile(p, re.IGNORECASE) for p in NON_HEALTH_PATTERNS]


# Check if the user's message indicates a medical emergency.
def check_emergency(text):
    for pattern in _EMERGENCY_RE:
        if pattern.search(text):
            return True
    return False


# Return the fixed emergency response message.
def get_emergency_response():
    return EMERGENCY_RESPONSE


# Check if user message is within healthcare domain scope.
def check_scope(text):
    text_lower = text.lower().strip()
    for pattern in _NON_HEALTH_RE:
        if pattern.search(text_lower):
            return False, (
                "I am a Healthcare Chatbot designed exclusively to assist with health-related topics "
                "(such as symptoms, medical conditions, nutrition, exercise, preventive care, "
                "and first aid). Please ask a health-related question!"
            )

    has_health_term = any(term in text_lower for term in HEALTH_TERMS)
    if not has_health_term:
        if re.search(r'\b(?:who\s+is|what\s+is\s+the|where\s+is|when\s+was|how\s+many\s+people|tell\s+me\s+about)\b', text_lower):
            return False, (
                "I am a Healthcare Chatbot designed exclusively to assist with health-related topics "
                "(such as symptoms, medical conditions, nutrition, exercise, preventive care, "
                "and first aid). How can I help with your health today?"
            )

    return True, None


# Run all pre-filters on user input.
def prefilter(text):
    if check_emergency(text):
        return False, get_emergency_response()
    in_scope, redirect = check_scope(text)
    if not in_scope:
        return False, redirect
    return True, None
