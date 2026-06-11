import random

# List of all possible data categories your system will use
CATEGORIES = ["medical", "finance", "images", "text", "general"]

def fake_type_checker(file_path: str):
    """
    This is a dummy function for development.
    Later, replace the inside with a real AI / classifier call.

    Returns:
        {
            "predicted_type": str,
            "confidence": float (0–1),
        }
    """

    # For now choose a type randomly
    predicted_type = random.choice(CATEGORIES)

    # Random confidence (0.55–0.99)
    confidence = round(random.uniform(0.55, 0.99), 2)

    return {
        "predicted_type": predicted_type,
        "confidence": confidence
    }


def match_selected_type(user_selected: str, predicted: str, confidence: float):
    """
    Returns YES/NO depending on if user_selected == predicted.
    """

    return {
        "user_selected": user_selected,
        "predicted": predicted,
        "confidence": confidence,
        "match": (user_selected == predicted)
    }
