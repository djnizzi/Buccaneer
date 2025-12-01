import re


def strip_video_tags(text):
    """
    Strips common video-related tags from a string (case-insensitive).
    
    Removes patterns like:
    - (Official Video)
    - [Official Video]
    - (Official Music Video)
    - [Official Music Video]
    - (Official Audio)
    - [Official Audio]
    - (Official Lyric Video)
    - [Official Lyric Video]
    - (Official HD Video)
    - [Official HD Video]
    - (Music Video)
    - [Music Video]
    - (Lyric Video)
    - [Lyric Video]
    - (Audio)
    - [Audio]
    - (Video)
    - [Video]
    - (Visualizer)
    - [Visualizer]
    - (Official Visualizer)
    - [Official Visualizer]
    
    Also strips leading and trailing whitespace.
    
    Args:
        text: The input string to process
        
    Returns:
        The cleaned string with video tags and extra whitespace removed
    """
    if not text:
        return text
    
    # Define patterns to remove (case-insensitive)
    # Using word boundaries and optional spaces for flexibility
    patterns = [
        r'[\(\[]?\s*Official\s+Music\s+Video\s*[\)\]]?',
        r'[\(\[]?\s*Official\s+Lyric\s+Video\s*[\)\]]?',
        r'[\(\[]?\s*Official\s+HD\s+Video\s*[\)\]]?',
        r'[\(\[]?\s*Official\s+Video\s*[\)\]]?',
        r'[\(\[]?\s*Official\s+Audio\s*[\)\]]?',
        r'[\(\[]?\s*Official\s+Visualizer\s*[\)\]]?',
        r'[\(\[]?\s*Music\s+Video\s*[\)\]]?',
        r'[\(\[]?\s*Lyric\s+Video\s*[\)\]]?',
        r'[\(\[]?\s*Visualizer\s*[\)\]]?',
        r'[\(\[]?\s*Video\s*[\)\]]?',
        r'[\(\[]?\s*Audio\s*[\)\]]?',
    ]
    
    result = text
    
    # Apply each pattern
    for pattern in patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE)
    
    # Strip leading and trailing whitespace
    result = result.strip()
    
    return result


# Example usage and tests
if __name__ == "__main__":
    test_cases = [
        "Song Title (Official Video)",
        "Song Title [Official Video]",
        "Song Title (Official Music Video)",
        "Song Title [Official Music Video]",
        "Song Title (official video)",  # lowercase
        "Song Title [OFFICIAL VIDEO]",  # uppercase
        "Song Title (Official Audio)",
        "Song Title [Official Lyric Video]",
        "Song Title (Music Video)",
        "Song Title [Lyric Video]",
        "Song Title (Visualizer)",
        "Song Title [Official Visualizer]",
        "Song Title (Official HD Video)",
        "  Song Title (Official Video)  ",  # with extra spaces
        "Song Title",  # no tag
        "Song Title (Official Video) (Official Audio)",  # multiple tags
    ]
    
    print("Testing strip_video_tags function:\n")
    for test in test_cases:
        result = strip_video_tags(test)
        print(f"Input:  '{test}'")
        print(f"Output: '{result}'")
        print()
