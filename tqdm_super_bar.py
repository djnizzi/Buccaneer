from tqdm import tqdm
import time
import random

def process_files(files):
    stats = {"auto": 0, "manual": 0, "skipped": 0, "haslyrics": 0}

    with tqdm(
        total=len(files),
        desc="🎵 Processing files",
        unit="file",
        colour="cyan",
        dynamic_ncols=True,
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
    ) as pbar:
        for file in files:
            time.sleep(0.01)  # simulate processing

            # Random fake decision for demo
            decision = random.choice(["auto", "manual", "skip", "haslyrics"])

            if decision == "auto":
                tqdm.write(f"🤖 Auto-tagged: {file}")
                stats["auto"] += 1
                pbar.colour = "green"

            elif decision == "manual":
                tqdm.write(f"🧠 Manual review: {file}")
                stats["manual"] += 1
                pbar.colour = "yellow"

            elif decision == "skip":
                tqdm.write(f"⏭️ Skipped: {file}")
                stats["skipped"] += 1
                pbar.colour = "red"

            else:
                stats["haslyrics"] += 1
                # Don’t log already tagged songs to avoid noise

            pbar.update(1)

    tqdm.write("\n✅ Processing complete.")
    tqdm.write(f"Auto: {stats['auto']}, Manual: {stats['manual']}, "
               f"Skipped: {stats['skipped']}, Has lyrics: {stats['haslyrics']}")
    return stats


# Example usage
if __name__ == "__main__":
    fake_files = [f"Track_{i}.mp3" for i in range(1, 51)]
    process_files(fake_files)
