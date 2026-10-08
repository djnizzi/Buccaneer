"""
compress_videos.py — the missing step between yt_video_dl.py and tag_videos.py.

Replaces the manual HandBrake pass: any video bigger than SIZE_THRESHOLD_MB is
re-encoded to a lower bitrate with the SAME resolution (no scaling ever), then:

  * kept    -> if the result is smaller than the original (the HandBrake rule)
  * kept    -> if the result is still over SIZE_THRESHOLD_MB but smaller
  * discarded -> "exception" case, result was bigger than the original, so the
                 original stays untouched

Safety rules that are not negotiable:
  1. The original is only deleted AFTER the new file passes ffprobe verification.
  2. Every run is recorded in a ledger so a file is never encoded twice
     (re-encoding an already-CRF-30 file is how you actually lose quality).
  3. HDR sources are skipped: libx264 CRF without tonemapping wrecks HDR colour.
  4. Temporary files live next to the original and are cleaned up on interrupt.

Usage:
  python compress_videos.py                      # whole folder, biggest wins first
  python compress_videos.py --dry-run            # show plan + estimates, encode nothing
  python compress_videos.py --limit 3            # try it on 3 files
  python compress_videos.py --only "BEACH HOUSE" # test one file
  python compress_videos.py --keep-original      # keep the old file next to the new one
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

from tqdm import tqdm

DOWNLOAD_DIR = r"W:\MusicClips\NowWatching"
FFMPEG_PATH = r"C:\Users\djniz\anaconda3\envs\python3_13\Library\bin"
LEDGER_FILE = "compressed_log.json"

SIZE_THRESHOLD_MB = 50     # only videos above this get re-encoded
# CRF for libx265. Measured against this library so the output lands at roughly the
# same bitrate HandBrake RF 30 produced (bpp ~0.054 on 1080p) -- but with visibly
# better quality, because x265 is far more efficient than x264.
# NOTE: x265 and x264 CRF scales are NOT interchangeable; do not copy an x264
# number across. Re-measure with --dry-run / a single test file if you change this.
CRF = 26
PRESET = "slow"            # slow = smallest file at the same quality, costs CPU time
AUDIO = "copy"             # copy = zero quality loss; "aac" = max player compatibility
MIN_SAVINGS = 0.0          # require at least this fraction smaller (0.05 = must save 5%)
VIDEO_CODEC = "libx265"    # HEVC: same visual quality as H.264 at ~60% of the bitrate

SUFFIX = ".shrink.tmp.mp4"   # in-progress encode, never a source
BACKUP_SUFFIX = ".orig.mp4"  # --keep-original backup

# Files carrying one of these in their `encoder` tag were already re-encoded by
# another tool. Compressing them again is the classic generation-loss trap, so
# they are skipped unless --reencode is passed.
ALREADY_ENCODED = ["handbrake"]   # yt-dlp's own "Lavf" tag does NOT match: raw downloads

MB = 1024 * 1024


# --------------------------------------------------------------------------- helpers

def human(size_bytes: float) -> str:
    return f"{size_bytes / MB:.1f} MB"


def fix_console_encoding() -> None:
    """Windows consoles default to cp1252 and hard-crash on emoji. Force UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def parse_rate(rate: str) -> float:
    """'30000/1001' -> 29.97, garbage -> 30.0"""
    try:
        num, _, den = rate.partition("/")
        den_val = float(den) if den else 1.0
        return float(num) / den_val if den_val else 30.0
    except (ValueError, ZeroDivisionError):
        return 30.0


# --------------------------------------------------------------------------- probing

def probe(path: str) -> dict:
    """Read stream layout with ffprobe. Raises RuntimeError if the file is unreadable."""
    cmd = [
        os.path.join(FFMPEG_PATH, "ffprobe.exe"),
        "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    fmt = data.get("format", {})

    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]

    # Which muxer/encoder wrote this file — used to spot files some other tool
    # already re-encoded for us.
    encoder = ""
    fmt_tags = fmt.get("tags") or {}
    if "encoder" in fmt_tags:
        encoder = str(fmt_tags["encoder"])
    if not encoder:
        for s in streams:
            tag = (s.get("tags") or {}).get("encoder")
            if tag:
                encoder = str(tag)
                break

    # An embedded cover is a video stream flagged attached_pic; it is never the
    # main picture and must be stream-copied, not re-encoded.
    covers = [s for s in videos if (s.get("disposition") or {}).get("attached_pic") == 1]
    main = next((s for s in videos if s not in covers), None)
    if main is None:
        raise RuntimeError("no real video stream (cover art only?)")

    return {
        "duration": float(fmt.get("duration") or main.get("duration") or 0.0),
        "size": int(fmt.get("size") or os.path.getsize(path)),
        "bit_rate": int(fmt.get("bit_rate") or 0),
        "encoder": encoder,
        "main": main,
        "covers": covers,
        "audios": audios,
        "video_ordinals": list(range(len(videos))),   # positions of all video streams
        "main_ordinal": videos.index(main),           # position of the real picture
        "audio_ordinals": list(range(len(audios))),    # -c:a:N indexes among audio streams
        "subs": [s for s in streams if s.get("codec_type") == "subtitle"],
    }


def already_encoded(info: dict) -> bool:
    """True if another tool (e.g. HandBrake) already re-encoded this file."""
    enc = (info.get("encoder") or "").lower()
    return any(marker in enc for marker in ALREADY_ENCODED)


def is_hdr(info: dict) -> bool:
    """PQ/HLG footage must not be naively CRF'd into SDR."""
    main = info["main"]
    if (main.get("color_transfer") or "") in ("smpte2084", "aribi-std-b67"):
        return True
    return (main.get("color_primaries") or "") == "bt2020" and \
           (main.get("color_transfer") or "") not in ("bt709", "smpte170m")


def pick_pix_fmt(info: dict) -> str:
    """
    Keep 10-bit as 10-bit (forcing yuv420p there would band badly); everything
    else is normalised to yuv420p for maximum device compatibility.
    """
    src = info["main"].get("pix_fmt") or "yuv420p"
    return src if "10" in src or "12" in src else "yuv420p"


def rough_estimate_bytes(info: dict) -> int:
    """
    Deliberately rough pre-flight guess, used only to avoid starting an encode we
    cannot finish on a full disk. ~30% of the source is generous for CRF 30.
    """
    return int(info["size"] * 0.30)


def free_space(path: str) -> int:
    drive = os.path.splitdrive(os.path.abspath(path))[0] + "\\"
    try:
        return shutil.disk_usage(drive).free
    except OSError:
        return 0


# --------------------------------------------------------------------------- encoding

def build_command(src: str, dst: str, info: dict, args) -> list:
    cmd = [
        os.path.join(FFMPEG_PATH, "ffmpeg.exe"),
        "-hide_banner", "-nostdin", "-y", "-i", src,
        # map every stream so cover art / subtitles survive untouched
        "-map", "0",
    ]

    # Re-encode the real picture only, at reduced bitrate. Resolution untouched.
    cmd += [
        f"-c:v:{info['main_ordinal']}", args.codec,
        "-crf", str(args.crf),
        "-preset", args.preset,
        "-pix_fmt", pick_pix_fmt(info),
    ]

    # ffmpeg tags HEVC as 'hev1' by default, which QuickTime / Safari / iOS /
    # Apple TV refuse to play. 'hvc1' is the widely compatible marker.
    if "265" in args.codec or "hevc" in args.codec.lower():
        cmd += [f"-tag:v:{info['main_ordinal']}", "hvc1"]

    # Any other video stream is cover art -> copy as-is.
    for ordinal in info["video_ordinals"]:
        if ordinal != info["main_ordinal"]:
            cmd += [f"-c:v:{ordinal}", "copy"]

    # Audio: copy keeps quality and costs nothing in size.
    for ordinal in info["audio_ordinals"]:
        cmd += [f"-c:a:{ordinal}", args.audio]

    cmd += ["-c:s", "copy", "-c:t", "copy"]
    cmd += [
        "-map_metadata", "0",
        "-map_chapters", "0",
        "-movflags", "+faststart",
        "-progress", "pipe:1", "-nostats",
        dst,
    ]
    return cmd


def run_encode(cmd: list, info: dict, label: str, err_log: str) -> bool:
    """Run ffmpeg, drawing a live progress bar. Returns True on success."""
    duration = info["duration"]
    with open(err_log, "w", encoding="utf-8", errors="replace") as err:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=err,
            text=True, errors="replace", bufsize=1,
        )

        bar = tqdm(total=max(duration, 1.0), unit="s", desc=label[:38],
                   dynamic_ncols=True, leave=False,
                   bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt}s [{elapsed}<{remaining}]")
        try:
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("out_time_us="):
                    try:
                        bar.update(max(int(line.split("=", 1)[1]) / 1_000_000 - bar.n, 0))
                    except ValueError:
                        pass
                elif line.startswith("out_time_ms="):
                    # ffmpeg's ms key is actually microseconds
                    try:
                        bar.update(max(int(line.split("=", 1)[1]) / 1_000_000 - bar.n, 0))
                    except ValueError:
                        pass
                elif line.startswith("progress=") and line.endswith("end"):
                    break
            proc.wait()
        finally:
            bar.close()

    if proc.returncode != 0:
        tail = ""
        try:
            with open(err_log, "r", encoding="utf-8", errors="replace") as fh:
                tail = " | ".join([ln.strip() for ln in fh if ln.strip()][-3:])
        except OSError:
            pass
        tqdm.write(f"   ffmpeg failed (exit {proc.returncode}) {tail}")
        return False
    return True


def verify(dst: str, src_duration: float) -> tuple:
    """Returns (ok, message). Confirms the new file is real, complete and complete-length."""
    if not os.path.exists(dst) or os.path.getsize(dst) == 0:
        return False, "output missing or empty"

    try:
        out = probe(dst)
    except (RuntimeError, json.JSONDecodeError) as exc:
        return False, f"unreadable output: {exc}"

    if src_duration > 0:
        drift = abs(out["duration"] - src_duration)
        if drift > max(1.0, src_duration * 0.02):
            return False, f"length drift {drift:.1f}s vs source {src_duration:.1f}s"
    return True, "ok"


# --------------------------------------------------------------------------- ledger

def load_ledger(path: str) -> dict:
    if not os.path.exists(path):
        return {"files": {}}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        data.setdefault("files", {})
        return data
    except (json.JSONDecodeError, OSError):
        return {"files": {}}


def save_ledger(path: str, ledger: dict) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(ledger, fh, indent=2, sort_keys=True)


def already_done(ledger: dict, name: str, size: int, mtime: float) -> bool:
    rec = ledger["files"].get(name)
    if not rec:
        return False
    return rec.get("result_size") == size and abs(rec.get("result_mtime", 0) - mtime) < 1


# --------------------------------------------------------------------------- main

def clean_stale_temps(directory: str) -> None:
    """Remove leftovers from a previous Ctrl+C / crash."""
    leftovers = [f for f in os.listdir(directory) if f.endswith(SUFFIX)]
    for name in leftovers:
        path = os.path.join(directory, name)
        try:
            os.remove(path)
            print(f"🧹 Removed stale temp: {name}")
        except OSError as exc:
            print(f"⚠️  Could not remove {name}: {exc}")


def select_files(directory: str, args) -> list:
    files = []
    for name in os.listdir(directory):
        low = name.lower()
        if not low.endswith(".mp4"):
            continue
        if low.endswith(".orig.mp4"):
            continue                      # backups from --keep-original
        if SUFFIX in low:                # our own temp, never a source
            continue
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            continue
        if os.path.getsize(path) <= args.threshold * MB:
            continue
        if args.only and args.only.lower() not in low:
            continue
        files.append(path)

    # biggest first: fastest space relief, and the files that matter most
    files.sort(key=lambda p: os.path.getsize(p), reverse=bool(not args.smallest_first))
    if args.limit:
        files = files[:args.limit]
    return files


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-encode oversized videos to a lower bitrate, same resolution.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dir", default=DOWNLOAD_DIR, help="folder to process")
    parser.add_argument("--threshold", type=float, default=SIZE_THRESHOLD_MB,
                        help="only touch videos bigger than this (MB)")
    parser.add_argument("--crf", type=int, default=CRF,
                        help="x264/265 quality: lower = bigger file, higher = smaller")
    parser.add_argument("--preset", default=PRESET, help="x264 preset: ultrafast..veryslow")
    parser.add_argument("--codec", default=VIDEO_CODEC,
                        help="libx264, libx265 or libsvtav1")
    parser.add_argument("--audio", default=AUDIO,
                        help="copy (lossless) or aac (best compatibility)")
    parser.add_argument("--min-savings", type=float, default=MIN_SAVINGS,
                        help="only accept the new file if at least this much smaller (0..1)")
    parser.add_argument("--limit", type=int, default=0, help="process at most N files (0 = all)")
    parser.add_argument("--only", default="", help="only files containing this substring")
    parser.add_argument("--smallest-first", action="store_true", help="process small files first")
    parser.add_argument("--keep-original", action="store_true",
                        help="rename the old file to *.orig.mp4 instead of deleting it")
    parser.add_argument("--force", action="store_true",
                        help="re-encode even if this file was compressed before")
    parser.add_argument("--reencode", action="store_true",
                        help="also touch files another tool (e.g. HandBrake) already encoded")
    parser.add_argument("--allow-hdr", action="store_true",
                        help="also compress HDR (can shift colours badly)")
    parser.add_argument("--ignore-space", action="store_true",
                        help="skip the free-space pre-flight check")
    parser.add_argument("--dry-run", action="store_true", help="show the plan, encode nothing")
    args = parser.parse_args()

    fix_console_encoding()

    directory = args.dir
    if not os.path.isdir(directory):
        print(f"❌ Folder not found: {directory}")
        return 1

    ledger_path = os.path.join(directory, LEDGER_FILE)
    ledger = load_ledger(ledger_path)
    if not args.dry_run:
        clean_stale_temps(directory)

    files = select_files(directory, args)
    if not files:
        print(f"Nothing to do: no .mp4 over {args.threshold:g} MB in {directory}")
        return 0

    total_in = sum(os.path.getsize(f) for f in files)
    print(f"\n🎬 {len(files)} video(s) over {args.threshold:g} MB  ({human(total_in)} total)")
    print(f"   encoder {args.codec} CRF {args.crf} preset {args.preset} | audio {args.audio}")
    print(f"   keep the new file only if it is smaller than the original\n")

    if args.dry_run:
        for path in files:
            try:
                info = probe(path)
                m = info["main"]
                note = ""
                if already_encoded(info):
                    note = "  [already encoded -> would skip]"
                elif is_hdr(info):
                    note = "  [HDR -> would skip]"
                est = rough_estimate_bytes(info)
                print(f"  {os.path.basename(path)[:52]:<54} "
                      f"{info['main']['codec_name']:>5} {m.get('width')}x{m.get('height')} "
                      f"{human(info['size']):>10}  ~{human(est)} after{note}")
            except (RuntimeError, OSError, KeyError) as exc:
                print(f"  {os.path.basename(path)[:52]:<54} unreadable: {exc}")
        print(f"\n🟡 Dry run — nothing was encoded.")
        return 0

    stats = {"shrunk": 0, "kept_original": 0, "skipped": 0, "failed": 0}
    saved = 0

    try:
        for path in tqdm(files, desc="🎞️  Compressing", unit="file",
                         dynamic_ncols=True, colour="cyan"):
            name = os.path.basename(path)
            src_size = os.path.getsize(path)

            if not args.force and already_done(ledger, name, src_size, os.path.getmtime(path)):
                tqdm.write(f"⏭️  Already compressed, skipping: {name}")
                stats["skipped"] += 1
                continue

            try:
                info = probe(path)
            except (RuntimeError, OSError, json.JSONDecodeError) as exc:
                tqdm.write(f"⚠️  Cannot read {name}: {exc}")
                stats["failed"] += 1
                continue

            if already_encoded(info) and not args.reencode:
                tqdm.write(f"🛡️  Already encoded by another tool "
                           f"({info['encoder'].split()[0]}), not touching: {name}")
                stats["skipped"] += 1
                continue

            if is_hdr(info) and not args.allow_hdr:
                tqdm.write(f"🛡️  Skipping HDR (colours would shift): {name}")
                stats["skipped"] += 1
                continue

            free = free_space(path)
            if not args.ignore_space and free < max(rough_estimate_bytes(info), 100 * MB):
                tqdm.write(f"💾 Not enough free space for {name} "
                           f"({human(free)} left) — skipping")
                stats["skipped"] += 1
                continue

            tmp = os.path.join(directory, os.path.splitext(name)[0] + SUFFIX)
            err_log = os.path.join(directory, os.path.splitext(name)[0] + ".ffmpeg.err")

            cmd = build_command(path, tmp, info, args)
            if not run_encode(cmd, info, name, err_log):
                for leftover in (tmp, err_log):
                    if os.path.exists(leftover):
                        os.remove(leftover)
                stats["failed"] += 1
                continue

            ok, why = verify(tmp, info["duration"])
            if not ok:
                tqdm.write(f"🛑 Verification failed ({why}) — keeping original: {name}")
                for leftover in (tmp, err_log):
                    if os.path.exists(leftover):
                        os.remove(leftover)
                stats["failed"] += 1
                continue

            new_size = os.path.getsize(tmp)
            if new_size < src_size * (1.0 - args.min_savings):
                if args.keep_original:
                    backup = os.path.join(directory, os.path.splitext(name)[0] + BACKUP_SUFFIX)
                    os.replace(path, backup)
                else:
                    os.remove(path)
                os.replace(tmp, path)
                if os.path.exists(err_log):
                    os.remove(err_log)

                ledger["files"][name] = {
                    "result_size": os.path.getsize(path),
                    "result_mtime": os.path.getmtime(path),
                    "original_size": src_size,
                    "crf": args.crf,
                    "preset": args.preset,
                    "codec": args.codec,
                    "date": datetime.now().isoformat(timespec="seconds"),
                }
                save_ledger(ledger_path, ledger)

                gain = src_size - new_size
                saved += gain
                stats["shrunk"] += 1
                pct = gain / src_size * 100
                flag = " (kept original too)" if args.keep_original else ""
                tqdm.write(f"✅ {name[:44]:<46} {human(src_size):>10} -> {human(new_size):>10} "
                           f"(-{pct:.0f}%){flag}")
            else:
                for leftover in (tmp, err_log):
                    if os.path.exists(leftover):
                        os.remove(leftover)
                stats["kept_original"] += 1
                tqdm.write(f"➖ {name[:44]:<46} result {human(new_size)} not smaller than "
                           f"{human(src_size)} — kept original")

    except KeyboardInterrupt:
        print("\n⛔ Interrupted — no original was lost. Re-run to continue.")
        return 130

    print(f"\n{'=' * 62}")
    print(f"Shrunk:            {stats['shrunk']}")
    print(f"Kept original:     {stats['kept_original']}  (result was not smaller)")
    print(f"Skipped:           {stats['skipped']}")
    print(f"Failed:            {stats['failed']}")
    print(f"Space reclaimed:   {human(saved)}")
    if args.keep_original and stats["shrunk"]:
        print(f"Backups kept as:   *.orig.mp4  (delete them once you are happy)")
    print(f"Log:               {ledger_path}")
    print(f"{'=' * 62}")
    return 0


if __name__ == "__main__":
    sys.exit(main())