import re


def remove_id(text):
    """Removes discord IDs from strings"""
    return re.sub(r"<@\d+>", "", text)


def split_message(message):
    """Split messages into 1999 character chunks (discord's message limit)"""
    return [message[i : i + 1999] for i in range(0, len(message), 2000)]


def filter_mentions(text):
    """Remove any broadcasts"""
    pattern = r"[@]?(\b(here|everyone|channel)\b)"
    filtered_text = re.sub(pattern, "", text)
    return filtered_text
