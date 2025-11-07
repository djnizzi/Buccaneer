import os
import numpy as np
import librosa
import librosa.feature
from mutagen.id3 import ID3, ID3NoHeaderError, TKEY, TBPM, TXXX
from mutagen.mp3 import MP3

SUPPORTED_EXTS = (".mp3", ".wav", ".flac", ".ogg", ".m4a")

# Camelot wheel mapping
CAMELOT_MAP = {
    "C major": "8B", "G major": "9B", "D major": "10B", "A major": "11B", "E major": "12B", "B major": "1B",
    "F# major": "2B", "C# major": "3B", "Ab major": "4B", "Eb major": "5B", "Bb major": "6B", "F major": "7B",
    "A minor": "8A", "E minor": "9A", "B minor": "10A", "F# minor": "11A", "C# minor": "12A", "G# minor": "1A",
    "D# minor": "2A", "A# minor": "3A", "F minor": "4A", "C minor": "5A", "G minor": "6A", "D minor": "7A"
}

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Krumhansl–Kessler key profiles (normalized)
MAJ_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                        2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MIN_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                        2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

def detect_key(y, sr):
    """Use Krumhansl-Schmuckler key estimation based on chroma CQT."""
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)

    # Compute correlations for each of the 12 transpositions
    corr_major = [np.correlate(np.roll(MAJ_PROFILE, i), chroma_mean)[0] for i in range(12)]
    corr_minor = [np.correlate(np.roll(MIN_PROFILE, i), chroma_mean)[0] for i in range(12)]

    max_major = np.argmax(corr_major)
    max_minor = np.argmax(corr_minor)

    if max(corr_major) >= max(corr_minor):
        return f"{NOTES[max_major]} major"
    else:
        return f"{NOTES[max_minor]} minor"

def detect_and_tag(file_path):
    print(f"\n🎵 Analyzing: {os.path.basename(file_path)}")

    try:
        y, sr = librosa.load(file_path, sr=None, mono=True)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(np.mean(tempo)) if isinstance(tempo, np.ndarray) else float(tempo)

        key_classical = detect_key(y, sr)
        key_camelot = CAMELOT_MAP.get(key_classical, "N/A")

        print(f" → Key: {key_classical} ({key_camelot}), BPM: {tempo:.1f}")

        if not file_path.lower().endswith(".mp3"):
            print("   ⚠️ Skipping (non-MP3 format)")
            return

        # Load or create ID3 tags
        try:
            id3 = ID3(file_path)
        except ID3NoHeaderError:
            audio = MP3(file_path)
            audio.add_tags()
            audio.save()
            id3 = ID3(file_path)

        # Write/update frames
        id3.delall("TKEY")
        id3.add(TKEY(encoding=3, text=[key_camelot]))

        id3.delall("TBPM")
        id3.add(TBPM(encoding=3, text=[str(int(round(tempo)))]))

        id3.delall("TXXX:CLASSICAL_KEY")
        id3.add(TXXX(encoding=3, desc="CLASSICAL_KEY", text=[key_classical]))

        id3.save()
        print("   ✔️ Tags saved (TKEY, TBPM, TXXX:CLASSICAL_KEY)\n")

    except Exception as e:
        print(f"   ⚠️ Error processing {file_path}: {e}")

def main():
    print("🎧 Key & BPM Tagger (Librosa + Traktor-compatible)\n")
    folder = input("Enter the path to your music folder: ").strip()

    if not os.path.isdir(folder):
        print("❌ Invalid folder path.")
        return

    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(SUPPORTED_EXTS):
                detect_and_tag(os.path.join(root, file))

    print("\n✅ Done! All compatible files processed.\n")

if __name__ == "__main__":
    main()

