import os
import shutil
import logging
from mutagen.id3 import ID3, APIC
from PIL import Image
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cover_art_processing.log"),
        logging.StreamHandler()
    ]
)

def is_image_file(filename):
    return filename.lower().endswith(('.jpg', '.jpeg', '.png'))

def is_jpg(filename):
    return filename.lower().endswith(('.jpg', '.jpeg'))

def process_albums(root_path):
    for root, dirs, files in os.walk(root_path):
        folder_name = os.path.basename(root)
        
        # Check for folder.jpg (case sensitive) - Skip if exists
        if "folder.jpg" in files:
            continue

        # Cleanup specific files
        if "Folder.jpg" in files:
            try:
                os.remove(os.path.join(root, "Folder.jpg"))
                logging.info(f"Deleted Folder.jpg in {root}")
            except OSError as e:
                logging.error(f"Error deleting Folder.jpg in {root}: {e}")

        if "AlbumArtSmall.jpg" in files:
            try:
                os.remove(os.path.join(root, "AlbumArtSmall.jpg"))
                logging.info(f"Deleted AlbumArtSmall.jpg in {root}")
            except OSError as e:
                logging.error(f"Error deleting AlbumArtSmall.jpg in {root}: {e}")

        # Skip folders starting with CD1, CD2, etc.
        if folder_name.upper().startswith("CD") and folder_name[2:].isdigit():
             continue
        
        # Re-scan files after deletions
        current_files = os.listdir(root)
        jpg_files = [f for f in current_files if is_jpg(f)]
        png_files = [f for f in current_files if f.lower().endswith('.png')]
        mp3_files = [f for f in current_files if f.lower().endswith('.mp3')]

        # Logic Branch 1: No JPG/JPEG files
        if not jpg_files:
            if mp3_files:
                first_mp3 = os.path.join(root, mp3_files[0])
                try:
                    audio = ID3(first_mp3)
                    found_art = False
                    for tag in audio.getall("APIC"):
                        if tag.mime in ['image/jpeg', 'image/jpg']:
                            with open(os.path.join(root, "folder.jpg"), 'wb') as f:
                                f.write(tag.data)
                            logging.info(f"Extracted folder.jpg from {first_mp3}")
                            found_art = True
                            break
                    if not found_art:
                        logging.warning(f"No suitable APIC tag found in {first_mp3}")
                except Exception as e:
                    logging.error(f"Error processing MP3 {first_mp3}: {e}")
            else:
                # No JPGs and no MP3s (or at least no MP3s to check)
                pass # Or log if needed, but prompt says "if there aren't files of type JPG... get first MP3"

        # Logic Branch 2: JPG/JPEG files exist
        else:
            resize_files = [f for f in jpg_files if f.lower().endswith(('_resize.jpg', '_resize.jpeg'))]
            
            if len(resize_files) > 1:
                logging.warning(f"Multiple _resize files in {root}. Skipping.")
                continue
            
            if png_files:
                logging.warning(f"PNG files found in {root}.")

            if len(resize_files) == 1:
                resize_file = resize_files[0]
                base_name = resize_file.rsplit('_resize', 1)[0]
                # Reconstruct original name extension (could be .jpg or .jpeg)
                # We need to find if a file exists that matches base_name + .jpg or .jpeg
                original_candidate = None
                for ext in ['.jpg', '.jpeg']:
                    if (base_name + ext) in current_files:
                        original_candidate = base_name + ext
                        break
                
                resize_file_path = os.path.join(root, resize_file)
                
                if original_candidate:
                    original_path = os.path.join(root, original_candidate)
                    try:
                        if os.path.getsize(original_path) < 200 * 1024: # 200kb
                            os.rename(original_path, os.path.join(root, "folder.jpg"))
                            os.remove(resize_file_path)
                            logging.info(f"Renamed {original_candidate} to folder.jpg and deleted {resize_file}")
                        else:
                            os.rename(resize_file_path, os.path.join(root, "folder.jpg"))
                            logging.info(f"Renamed {resize_file} to folder.jpg (original too big)")
                    except OSError as e:
                        logging.error(f"Error handling resize file in {root}: {e}")
                else:
                    try:
                        os.rename(resize_file_path, os.path.join(root, "folder.jpg"))
                        logging.info(f"Renamed {resize_file} to folder.jpg (no original found)")
                    except OSError as e:
                        logging.error(f"Error renaming {resize_file} in {root}: {e}")

            # Logic Branch 3: No _resize files (or at least not handled above? Prompt says "if there is just one... else if...")
            # The prompt structure implies:
            # if > 1 resize: skip
            # if 1 resize: handle
            # else (implies 0 resize files): check cover/front
            elif len(resize_files) == 0:
                candidates = ["cover.jpg", "cover.jpeg", "front.jpg", "front.jpeg"]
                found_candidate = None
                # Case insensitive search
                lower_map = {f.lower(): f for f in current_files}
                
                for cand in candidates:
                    if cand in lower_map:
                        found_candidate = lower_map[cand]
                        break
                
                if found_candidate:
                    cand_path = os.path.join(root, found_candidate)
                    try:
                        if os.path.getsize(cand_path) < 200 * 1024:
                            os.rename(cand_path, os.path.join(root, "folder.jpg"))
                            logging.info(f"Renamed {found_candidate} to folder.jpg")
                        else:
                            # Resize
                            with Image.open(cand_path) as img:
                                aspect_ratio = img.height / img.width
                                new_height = int(640 * aspect_ratio)
                                img_resized = img.resize((640, new_height), Image.Resampling.LANCZOS)
                                img_resized.save(os.path.join(root, "folder.jpg"))
                                logging.info(f"Resized {found_candidate} to folder.jpg")
                    except Exception as e:
                        logging.error(f"Error processing candidate {found_candidate} in {root}: {e}")

if __name__ == "__main__":
    # root_directory = r"X:\Albums"
    root_directory = r"X:\Albums"
    
    if os.path.exists(root_directory):
        print(f"Starting processing on {root_directory}...")
        process_albums(root_directory)
        print("Done.")
    else:
        print(f"Directory {root_directory} not found. Please check the path.")



