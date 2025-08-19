import re
def extract_session_id(session_str: str):
    match=re.search(r"/sessions/(.*?)/contexts/",session_str)
    if match:
        extracted_str=match.group(1)
        return extracted_str
    return ""

def get_items_from_food_dict(food_dict: dict):
    return ", ".join([f"{int(val)} {key}" for key,val in food_dict.items()])
