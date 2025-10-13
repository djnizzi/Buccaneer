def inspect(obj, maxlen=120):
    """
    Pretty-print attributes and values of an object.
    Falls back gracefully if attribute access fails.
    """
    print(f"🔎 Inspecting object of type: {type(obj)}\n")
    for attr in dir(obj):
        if attr.startswith("_"):  # skip private/internal
            continue
        try:
            value = getattr(obj, attr)
            # truncate long values for readability
            val_str = str(value)
            if len(val_str) > maxlen:
                val_str = val_str[:maxlen] + "..."
            print(f"{attr:20} = {val_str}")
        except Exception as e:
            print(f"{attr:20} = <Error: {e}>")