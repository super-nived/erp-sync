def paginate(items: list, page: int, size: int) -> dict:
    start = (page - 1) * size
    end = start + size
    return {
        "items": items[start:end],
        "page": page,
        "size": size,
        "total": len(items),
    }
