from collections import defaultdict

# 기본 known 매핑
KNOWN_PREFIX = {
    "IPX": "IdeaPocket",
    "SSIS": "S1",
    "MIDE": "Moodyz",
    "PRED": "Premium",
}


def classify(items):
    grouped = defaultdict(list)

    for item in items:
        prefix = item["prefix"]
        grouped[prefix].append(item)

    result = []

    for prefix, group in grouped.items():
        result.append({
            "prefix": prefix,
            "count": len(group),
            "studio": KNOWN_PREFIX.get(prefix, "UNKNOWN"),
            "samples": group[:3]   # 샘플만
        })

    return sorted(result, key=lambda x: -x["count"])