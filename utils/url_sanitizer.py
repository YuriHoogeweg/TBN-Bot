import re

def sanitize_url_in_text(text: str, url: str) -> str:
    # Escape special regex characters in the URL
    escaped_url = re.escape(url)
    
    # Pattern to match the URL with optional surrounding characters
    pattern = r'([^\s]?)(' + escaped_url + r')([^\s]?)'
    
    def replace_func(match):
        before, matched_url, after = match.groups()
        
        # Add space before if there's a non-space character before the URL
        if before and before != ' ':
            matched_url = ' ' + matched_url
        
        # Add space after if there's a non-space character after the URL
        if after and after != ' ':
            matched_url = matched_url + ' '
        
        return matched_url

    # Replace the URL in the text, adding spaces if necessary
    sanitized_text = re.sub(pattern, replace_func, text)
    
    return sanitized_text

# Example usage:
# response = "Check out this stream:https://twitch.tv/example!It's great!"
# stream_url = "https://twitch.tv/example"
# sanitized_response = sanitize_url_in_text(response, stream_url)
# print(sanitized_response)
# Output: "Check out this stream: https://twitch.tv/example !It's great!"