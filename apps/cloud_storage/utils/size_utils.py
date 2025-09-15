def mb_to_human_gb(mb_value: int) -> str:
    """
    Convert a value in MB to a human-readable GB string.

    Example:
        mb_to_human_gb(5000)  # -> "5 GB"
        mb_to_human_gb(1536)  # -> "2 GB"
    """
    if mb_value is None:
        return "0.0 GB"

    gb_value = mb_value / 1000
    return f"{gb_value} GB"
