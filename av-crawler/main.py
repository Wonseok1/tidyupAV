from crawler import fetch_html, extract_items
from parser import parse_code
from classifier import classify

URL = "https://example.com"  # 크롤링 대상


def main():
    html = fetch_html(URL)
    raw_items = extract_items(html)

    parsed = []
    for item in raw_items:
        data = parse_code(item)
        if data:
            parsed.append(data)

    result = classify(parsed)

    for r in result:
        print(f"{r['prefix']} ({r['studio']}) - {r['count']}")
        for s in r["samples"]:
            print("   ", s["raw"])


if __name__ == "__main__":
    main()