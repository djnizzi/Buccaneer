import sys
import os

# Add current directory to path to allow importing 1001tracklists
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from importlib import import_module
tracklists_module = import_module("1001tracklists")
Tracklist = tracklists_module.Tracklist

def time_to_frames(time_str):
    """
    Convert a time string (MM:SS or H:MM:SS) to CUE time format (MM:SS:FF).
    CUE sheets use 75 frames per second.
    """
    if not time_str:
        return "00:00:00"
    
    parts = time_str.split(':')
    if len(parts) == 2:
        m, s = parts
        h = 0
    elif len(parts) == 3:
        h, m, s = parts
    else:
        return "00:00:00" # Fallback
    
    total_minutes = int(h) * 60 + int(m)
    seconds = int(s)
    
    # Format: MM:SS:FF (Frames are 00 for simple timestamps)
    return f"{total_minutes:02d}:{seconds:02d}:00"

def generate_cue(url, output_file=None):
    from bs4 import BeautifulSoup
    
    if os.path.isfile(url):
        print(f"Reading tracklist from file: {url}")
        with open(url, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")
        tl = Tracklist(soup=soup)
        # If title is generic because of local file, try to get it from filename
        if not tl.title or "1001Tracklists" in tl.title:
             tl.title = os.path.splitext(os.path.basename(url))[0]
    else:
        print(f"Fetching tracklist from {url}...")
        tl = Tracklist(url)
    
    if not output_file:
        # Sanitize title for filename
        safe_title = "".join([c for c in tl.title if c.isalpha() or c.isdigit() or c==' ']).rstrip()
        output_file = f"{safe_title}.cue"
    
    print(f"Generating CUE sheet: {output_file}")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        performer = " & ".join(tl.DJs) if tl.DJs else "Unknown Artist"
        f.write(f'PERFORMER "{performer}"\n')
        f.write(f'TITLE "{tl.title}"\n')
        f.write(f'FILE "{tl.title}.mp3" MP3\n') # Placeholder filename
        
        track_num = 1
        for track in tl.tracks:
            # Collect all titles and performers (main track + subsongs)
            titles = [track.title]
            performers = [track.full_artist]
            
            for sub in track.subsongs:
                titles.append(sub.title)
                performers.append(sub.full_artist)
            
            # Concatenate with " / "
            final_title = " / ".join(titles)
            final_performer = " / ".join(performers)
            
            # Use main track's cue time
            m, s = divmod(track.cue_seconds, 60)
            cue_time = f"{m:02d}:{s:02d}"
            
            f.write(f'  TRACK {track_num:02d} AUDIO\n')
            f.write(f'    TITLE "{final_title}"\n')
            f.write(f'    PERFORMER "{final_performer}"\n')
            f.write(f'    INDEX 01 {time_to_frames(cue_time)}\n')
            track_num += 1

    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_cue.py <1001tracklists_page.html> [output_file]")
    else:
        url = sys.argv[1]
        outfile = sys.argv[2] if len(sys.argv) > 2 else None
        generate_cue(url, outfile)
