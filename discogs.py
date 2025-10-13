import configparser
import discogs_client
from rapidfuzz import fuzz
from utils import strip_feat

# --- CONFIG ---
config = configparser.ConfigParser()
config.read('secrets.ini')
discogs_api_key = config['API']['key']
appname = config['APP']['appname']
version = config['APP']['version']
app = appname + "/" + version

# Init clients
d = discogs_client.Client(app, user_token=discogs_api_key)

# --- Search Discogs ---
def search_discogs(query: str, max_results: int = 15, top_n: int = 5):
    print(f"🔍 Searching Discogs with query: {query}")


    results = d.search(query, type="release")

    if not results:
            print(f"⚠️ No Discogs results for query: {query}")
            return None

    # Build candidate list with deduplication
    candidates = []
    seen_ids = set()
    for i, r in enumerate(results):
        if i >= max_results:
            break
        if r.id in seen_ids:
            continue
        seen_ids.add(r.id)
        artist_names = []
        for a in getattr(r, "artists", []):
            if isinstance(a, dict):
                artist_names.append(a.get("name", "Unknown"))
            else:
                artist_names.append(getattr(a, "name", "Unknown"))
        artist_names = ", ".join(artist_names)

        candidate_title = f"{artist_names} - {r.title}"
        candidates.append((candidate_title, r))

    if not candidates:
        print("⚠️ No unique candidates found")
        return None

    # Compute fuzzy scores
    scored = []
    for title, release in candidates:
        score = fuzz.token_sort_ratio(query, title)
        scored.append((score, title, release))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Display top matches with details
    n_display = min(top_n, len(scored))
    print("\nTop matches:")
    for idx in range(n_display):
        score, title, release = scored[idx]

        try:
            # fetch full release details
            full_release = d.release(release.id)
        except Exception as e:
            print(f"⚠️ Could not fetch full release {release.id}: {e}")
            continue

        # Labels
        labels_list = []
        for l in getattr(full_release, "labels", []):
              if isinstance(l, dict):
                labels_list.append(l.get("name", "Unknown"))
              else:
                labels_list.append(getattr(l, "name", "Unknown"))
        labels = ", ".join(labels_list)

        # Formats
        formats_list = []
        for f in getattr(full_release, "formats", []):
            fmt_name = getattr(f, "name", f.get("name", "Unknown") if isinstance(f, dict) else "Unknown")
            descs = getattr(f, "descriptions", f.get("descriptions", []) if isinstance(f, dict) else [])
            formats_list.append(f"{fmt_name} ({', '.join(descs)})" if descs else fmt_name)
        formats = ", ".join(formats_list)

        country = getattr(full_release, "country", "Unknown")
        released = (
                getattr(full_release, "released", None)
                or full_release.data.get("released")
                or full_release.data.get("released_formatted")
        )
        if not released and getattr(full_release, "master_id", None):
            try:
                master = d.master(full_release.master_id)
                released = getattr(master, "released", None)
            except Exception:
                pass

        # Step 3: fallback to year
        if not released:
            released = str(getattr(full_release, "year", "Unknown"))

        print(f"{idx + 1}. {title}, {released}, {labels}, {country}, {formats} - {score:.2f}%")

    # Skip choice if only one release
    # if len(scored) == 1:
    #     selected_release = scored[0][2]
    #     print(f"✅ Only one match, automatically selected: {scored[0][1]}")
    #     return selected_release

    # Otherwise ask user
    while True:
        choice = input(f"Choose a release [1-{min(top_n, len(scored))}] or 0 to skip: ")
        if choice.isdigit():
            choice = int(choice)
            if 0 <= choice <= min(top_n, len(scored)):
                break
        print("Invalid input, try again.")

    if choice == 0:
        print("Skipped.")
        return None

    selected_release = scored[choice - 1][2]
    print(f"✅ You selected: {scored[choice - 1][1]}")
    return selected_release


def search_discogs_with_prompt(query: str):
    # Strip feat./ft. for Discogs search
    cleaned_query = strip_feat(query)

    # Ask user if they want to proceed with the cleaned query
    print(f"\n🔍 Proposed Discogs query: \"{cleaned_query}\" (from \"{query}\")")
    choice = input("Press [Enter] to search, or type a custom query (or 0 to skip): ").strip()

    if choice == "0":
        print("⏭️ Skipping Discogs search.")
        return None
    elif choice:
        cleaned_query = choice  # user override

    # Continue with normal search
    return search_discogs(cleaned_query)