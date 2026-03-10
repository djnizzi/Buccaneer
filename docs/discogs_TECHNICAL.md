# Discogs Searcher Technical Documentation

`discogs.py` is a utility module that handles all communication with the Discogs API.

## Core Functions

### `search_discogs(query, max_results=15, top_n=5)`
The primary search engine.
1. **Search**: Executes a `release` type search on Discogs.
2. **Deduplication**: Filters out duplicate release IDs from the result set.
3. **Fuzzy Scoring**: Calculates `fuzz.token_sort_ratio` between the query and the string `"{Artists} - {Title}"`.
4. **Detail Fetching**: For the top `n` candidates, it performs a secondary API call (`d.release(id)`) to fetch rich metadata:
   - Labels
   - Formats (including descriptions like "Limited Edition")
   - Country
   - Release Date (with fallback to Master Release date or Year).

### `search_discogs_with_prompt(query)`
The interactive wrapper.
1. **Normalization**: Calls `utils.strip_feat` to clean the input.
2. **User Input**: Allows the user to override the query before actually hitting the API.
3. **Delegation**: Calls `search_discogs` with the final query.

## Integration Details

- **Client Initialization**: Uses `discogs_client.Client` with a user-agent string constructed from `secrets.ini`.
- **Fuzzy Logic**: Powered by `rapidfuzz`. The `token_sort_ratio` is chosen because it handles word order differences well (e.g., "Artist - Title" vs "Title - Artist").
- **Data Model**: The script carefully handle's Discogs' inconsistent data structures (e.g., `labels` and `formats` can sometimes be dictionaries or objects depending on the cache state/API version).

## Performance Considerations

- **Rate Limiting**: Discogs has strict rate limits (60 requests per minute). The script minimizes calls by only fetching full details for the top `top_n` results rather than the entire search page.
- **Caching**: While the script doesn't implement local caching, the `discogs_client` library has built-in mechanisms that the script relies on.
