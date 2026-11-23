from app.services.constants import load_constants
from app.services.rules import classify


def build_dashboard(records: list[dict], filters: dict[str, str], source: dict) -> dict:
    labels = load_constants()["filters"]
    rules = load_constants()["classification"]
    periods = sorted({row["period"] for row in records})
    municipalities = sorted({row["zone"] for row in records})
    violence_types = sorted({row["violence"] for row in records})
    service_types = sorted({row["service"] for row in records})

    def selected(row: dict) -> bool:
        if filters["period"] != labels["allPeriods"] and row["period"] != filters["period"]:
            return False
        if filters["municipality"] != labels["allZones"] and row["zone"] != filters["municipality"]:
            return False
        if filters["violence"] != labels["allViolence"] and row["violence"] != filters["violence"]:
            return False
        if filters["service"] != labels["allServices"] and row["service"] != filters["service"]:
            return False
        return True

    filtered = [row for row in records if selected(row)]
    grouped: dict[str, dict] = {}
    for row in filtered:
        bucket = grouped.setdefault(
            row["zone"],
            {"name": row["zone"], "cases": 0.0, "capacity": 0.0, "count": 0},
        )
        bucket["cases"] += row["cases"]
        bucket["capacity"] += row["capacity"]
        bucket["count"] += 1

    summaries = []
    for bucket in grouped.values():
        ratio = bucket["cases"] / bucket["capacity"] if bucket["capacity"] else rules["missingCapacityRatio"]
        summaries.append(
            {
                "name": bucket["name"],
                "cases": bucket["cases"],
                "capacity": bucket["capacity"],
                "ratio": ratio,
                "count": bucket["count"],
                "classification": classify(ratio, bucket["cases"]),
            }
        )
    summaries.sort(key=lambda item: item["ratio"], reverse=True)

    trend_scope = [
        row
        for row in records
        if filters["municipality"] == labels["allZones"] or row["zone"] == filters["municipality"]
    ]
    trends = []
    for period in periods[-5:]:
        subset = [row for row in trend_scope if row["period"] == period]
        trends.append(
            {
                "period": period,
                "cases": sum(row["cases"] for row in subset),
                "capacity": sum(row["capacity"] for row in subset),
            }
        )

    return {
        "periods": periods,
        "municipalities": municipalities,
        "violenceTypes": violence_types,
        "serviceTypes": service_types,
        "summaries": summaries,
        "trends": trends,
        "totalCases": sum(row["cases"] for row in filtered),
        "totalCapacity": sum(row["capacity"] for row in filtered),
        "priorityCount": sum(1 for item in summaries if item["ratio"] >= rules["priorityRatio"]),
        "source": source,
    }
