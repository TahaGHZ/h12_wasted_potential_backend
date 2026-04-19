import csv
import json
import math
import os
from datetime import datetime, timedelta
from typing import Any

from backend.config.llm import LLMService

DATA_PATH = os.path.join(os.path.dirname(__file__), "prepared_risk_data.csv")
HISTORY_PATH = os.path.join(os.path.dirname(__file__), "ai_history.json")

AQI_LABELS = {
    1: "Good",
    2: "Fair",
    3: "Moderate",
    4: "Poor",
    5: "Very Poor",
}

PM10_THRESHOLDS = [
    (45.0, "safe"),
    (100.0, "moderate"),
    (250.0, "high"),
    (float("inf"), "critical"),
]

SO2_THRESHOLDS = [
    (40.0, "safe"),
    (120.0, "moderate"),
    (350.0, "high"),
    (float("inf"), "critical"),
]

LEVEL_ORDER = {
    "safe": 0,
    "moderate": 1,
    "high": 2,
    "critical": 3,
    "unknown": -1,
}

ALERT_MESSAGES = {
    "safe": "Air quality is safe. Enjoy outdoor activities.",
    "moderate": "Moderate air quality. Sensitive groups should reduce prolonged exposure.",
    "high": "Poor air quality. Limit outdoor activity and use protection.",
    "critical": "Critical air quality. Stay indoors and follow emergency guidance.",
}


def _parse_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _load_rows() -> list[dict[str, Any]]:
    if not os.path.exists(DATA_PATH):
        return []

    rows = []
    with open(DATA_PATH, "r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(row)
    return rows


def _level_from_thresholds(value: float | None, thresholds: list[tuple[float, str]]) -> str:
    if value is None:
        return "unknown"
    for limit, level in thresholds:
        if value < limit:
            return level
    return "unknown"


def _aggregate_level(levels: list[str]) -> str:
    if not levels:
        return "unknown"
    return max(levels, key=lambda level: LEVEL_ORDER.get(level, -1))


def _aqi_label(value: int | None) -> str:
    if value is None:
        return "Unknown"
    return AQI_LABELS.get(value, "Unknown")


def _build_alert(level: str) -> dict[str, Any]:
    return {
        "level": level,
        "message": ALERT_MESSAGES.get(level, "Air quality data unavailable."),
        "should_alert": LEVEL_ORDER.get(level, -1) >= LEVEL_ORDER["moderate"],
    }


def _load_reasoning_history() -> dict[str, str]:
    if not os.path.exists(HISTORY_PATH):
        return {}
    try:
        with open(HISTORY_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_reasoning_history(history: dict[str, str]) -> None:
    with open(HISTORY_PATH, "w", encoding="utf-8") as handle:
        json.dump(history, handle, indent=2)


def _day_key(value: str | None) -> str | None:
    if not value:
        return None
    timestamp = _parse_timestamp(value)
    if not timestamp:
        return None
    return timestamp.date().isoformat()


def _select_peak_row(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    peak_row = None
    peak_value = float("-inf")
    for row in rows:
        pm10 = _parse_float(row.get("pm10"))
        if pm10 is None:
            continue
        if pm10 > peak_value:
            peak_value = pm10
            peak_row = row
    return peak_row or (rows[-1] if rows else None)


def _build_reasoning_prompt(day: str, peak_row: dict[str, Any], prev_summary: str) -> str:
    pm10 = _parse_float(peak_row.get("pm10"))
    so2 = _parse_float(peak_row.get("so2"))
    cardinal = peak_row.get("cardinal") or "Unknown"

    return (
        "SYSTEM: Environmental Auditor for Gabes, Tunisia.\n"
        "WHO & NATIONAL REFERENCE THRESHOLDS (24h Concentration):\n"
        "- PM10 (Particulate Matter):\n"
        "  * Safe: < 45 ug/m3\n"
        "  * Moderate: 45 - 100 ug/m3\n"
        "  * High: 100 - 250 ug/m3\n"
        "  * Critical: > 250 ug/m3\n"
        "- SO2 (Sulfur Dioxide):\n"
        "  * Safe: < 40 ug/m3\n"
        "  * Moderate: 40 - 120 ug/m3\n"
        "  * High: 120 - 350 ug/m3\n"
        "  * Critical: > 350 ug/m3\n\n"
        f"CURRENT DATA FOR {day}:\n"
        f"- Peak PM10: {pm10 if pm10 is not None else 'n/a'} ug/m3\n"
        f"- Peak SO2: {so2 if so2 is not None else 'n/a'} ug/m3\n"
        f"- Wind Direction: {cardinal} (Coming FROM {cardinal})\n\n"
        "GEOGRAPHIC RISK FACTORS:\n"
        "- NORTH/NORTH-EAST Wind: High risk (Pollution moves toward Gabes City and Teboulbou).\n"
        "- WEST/SOUTH Wind: Lower risk (Pollution moves toward the Sea).\n\n"
        "TASK:\n"
        "1. Assign a RISK SCORE (0 to 10).\n"
        "2. Compare current values against the Reference Thresholds.\n"
        "3. Compare today's trend with yesterday's summary (use 'Baseline' if no prior day).\n"
        f"Yesterday summary: {prev_summary}\n\n"
        "FORMAT:\n"
        f"## Report for {day}\n"
        "**RISK SCORE:** [Score]/10\n"
        "**Health Status:** [Safe / Warning / Danger / Critical]\n"
        "**Trend vs Yesterday:** [Improved / Worsened / Stable / Baseline]\n"
        "**Auditor Summary:** [Provide explanation]"
    )


def _normalize_summary(summary: str) -> str:
    if not summary:
        return summary
    normalized = summary.replace(
        "**Trend vs Yesterday:** No comparison available",
        "**Trend vs Yesterday:** Baseline",
    )
    return normalized


def _group_rows_by_day(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    day_groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        day = _day_key(row.get("timestamp"))
        if not day:
            continue
        day_groups.setdefault(day, []).append(row)
    return day_groups


def _ensure_day_summaries(
    day_groups: dict[str, list[dict[str, Any]]],
    day_keys: list[str],
    history: dict[str, str],
    llm: LLMService,
    previous_summary: str,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    previous_summary = previous_summary or "Baseline for comparison."

    for day in day_keys:
        if day in history:
            summary_text = _normalize_summary(history[day])
            history[day] = summary_text
            source = "cache"
        else:
            peak_row = _select_peak_row(day_groups.get(day, []))
            if peak_row is None:
                continue
            prompt = _build_reasoning_prompt(day, peak_row, previous_summary)
            summary_text = llm.generate_text(system_prompt="", user_prompt=prompt, temperature=0.2, max_tokens=700)
            summary_text = _normalize_summary(summary_text)
            history[day] = summary_text
            source = "generated"
        previous_summary = summary_text
        summaries.append({"date": day, "summary": summary_text, "source": source})

    return summaries


def _build_period_prompt(day_summaries: list[dict[str, Any]], period_label: str) -> str:
    summaries_text = "\n\n".join(
        f"### {item['date']}\n{item['summary']}" for item in day_summaries
    )
    return (
        "SYSTEM: Environmental Auditor for Gabes, Tunisia.\n"
        "TASK: Summarize the last 3 days of air quality into one concise report.\n"
        "Focus on overall trend, highest risk period, and any shift in wind risk.\n"
        "OUTPUT FORMAT:\n"
        f"## 3-day Report ({period_label})\n"
        "**Overall Trend:** [Improved / Worsened / Mixed / Stable]\n"
        "**Highest Risk Day:** [Date + short reason]\n"
        "**Summary:** [Short paragraph]\n\n"
        "INPUT DAILY REPORTS:\n"
        f"{summaries_text}"
    )


def _get_period_reasoning(rows: list[dict[str, Any]], days: int = 3) -> dict[str, Any] | None:
    if not rows:
        return None

    day_groups = _group_rows_by_day(rows)
    if not day_groups:
        return None

    day_keys = sorted(day_groups.keys())
    recent_days = day_keys[-days:] if len(day_keys) >= days else day_keys
    if not recent_days:
        return None

    prev_day_summary = "Baseline for comparison."
    first_day_index = day_keys.index(recent_days[0])
    if first_day_index > 0:
        prev_day_key = day_keys[first_day_index - 1]
        prev_day_summary = _load_reasoning_history().get(prev_day_key, prev_day_summary)

    period_label = f"{recent_days[0]} to {recent_days[-1]}"
    period_key = f"period:{recent_days[0]}:{recent_days[-1]}"

    history = _load_reasoning_history()
    try:
        llm = LLMService()
    except Exception:
        llm = None

    day_summaries: list[dict[str, Any]] = []
    if llm is not None:
        day_summaries = _ensure_day_summaries(day_groups, recent_days, history, llm, prev_day_summary)
        try:
            _save_reasoning_history(history)
        except OSError:
            pass

    if period_key in history:
        period_summary = history[period_key]
        period_source = "cache"
    elif llm is not None and day_summaries:
        prompt = _build_period_prompt(day_summaries, period_label)
        period_summary = llm.generate_text(system_prompt="", user_prompt=prompt, temperature=0.2, max_tokens=700)
        history[period_key] = period_summary
        period_source = "generated"
        try:
            _save_reasoning_history(history)
        except OSError:
            pass
    else:
        return None

    return {
        "date": period_label,
        "summary": period_summary,
        "source": period_source,
        "days": day_summaries,
    }


def _linear_regression(values: list[float]) -> tuple[float, float]:
    n = len(values)
    if n < 2:
        return 0.0, values[-1] if values else 0.0

    sum_x = sum(range(n))
    sum_y = sum(values)
    sum_xx = sum(i * i for i in range(n))
    sum_xy = sum(i * y for i, y in enumerate(values))

    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return 0.0, values[-1]

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def _regression_metrics(values: list[float]) -> dict[str, float]:
    if not values:
        return {
            "slope": 0.0,
            "intercept": 0.0,
            "r2": 0.0,
            "rmse": 0.0,
            "mae": 0.0,
        }

    slope, intercept = _linear_regression(values)
    n = len(values)
    predictions = [slope * idx + intercept for idx in range(n)]
    errors = [values[idx] - predictions[idx] for idx in range(n)]

    ss_res = sum(error * error for error in errors)
    mean_val = sum(values) / n
    ss_tot = sum((value - mean_val) ** 2 for value in values)
    r2 = 0.0 if ss_tot == 0 else 1 - (ss_res / ss_tot)
    rmse = math.sqrt(ss_res / n)
    mae = sum(abs(error) for error in errors) / n

    return {
        "slope": slope,
        "intercept": intercept,
        "r2": r2,
        "rmse": rmse,
        "mae": mae,
    }


def _forecast_series(values: list[float], hours_ahead: int, step_hours: int) -> list[float]:
    slope, intercept = _linear_regression(values)
    n = len(values)
    forecasts = []
    for hour in range(step_hours, hours_ahead + 1, step_hours):
        idx = (n - 1) + hour
        forecasts.append(slope * idx + intercept)
    return forecasts


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def _build_current(row: dict[str, Any]) -> dict[str, Any]:
    aqi = _parse_int(row.get("aqi"))
    pm10 = _parse_float(row.get("pm10"))
    so2 = _parse_float(row.get("so2"))
    wind_speed = _parse_float(row.get("wind_speed"))
    wind_direction = _parse_float(row.get("wind_direction"))

    pm10_level = _level_from_thresholds(pm10, PM10_THRESHOLDS)
    so2_level = _level_from_thresholds(so2, SO2_THRESHOLDS)
    aqi_level = _level_from_thresholds(float(aqi) if aqi is not None else None, [(2, "safe"), (3, "moderate"), (4, "high"), (6, "critical")])

    overall_level = _aggregate_level([pm10_level, so2_level, aqi_level])

    alert = _build_alert(overall_level)

    return {
        "timestamp": row.get("timestamp"),
        "aqi": aqi,
        "aqi_label": _aqi_label(aqi),
        "pm10": pm10,
        "so2": so2,
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
        "cardinal": row.get("cardinal"),
        "level": overall_level,
        "alert": alert,
    }


def _build_forecast(rows: list[dict[str, Any]], hours_ahead: int, step_hours: int) -> list[dict[str, Any]]:
    if not rows:
        return []

    parsed_times = [_parse_timestamp(row.get("timestamp", "")) for row in rows]
    timestamps = [t for t in parsed_times if t is not None]
    if not timestamps:
        return []

    last_timestamp = max(timestamps)

    aqi_values = [float(_parse_int(row.get("aqi")) or 0) for row in rows]
    pm10_values = [float(_parse_float(row.get("pm10")) or 0) for row in rows]
    so2_values = [float(_parse_float(row.get("so2")) or 0) for row in rows]

    aqi_forecast = _forecast_series(aqi_values, hours_ahead, step_hours)
    pm10_forecast = _forecast_series(pm10_values, hours_ahead, step_hours)
    so2_forecast = _forecast_series(so2_values, hours_ahead, step_hours)

    forecast_points = []
    for idx, hour in enumerate(range(step_hours, hours_ahead + 1, step_hours)):
        target_time = last_timestamp + timedelta(hours=hour)
        aqi_val = int(round(_clamp(aqi_forecast[idx], 1, 5)))
        pm10_val = _clamp(pm10_forecast[idx], 0, 2000)
        so2_val = _clamp(so2_forecast[idx], 0, 500)

        pm10_level = _level_from_thresholds(pm10_val, PM10_THRESHOLDS)
        so2_level = _level_from_thresholds(so2_val, SO2_THRESHOLDS)
        aqi_level = _level_from_thresholds(float(aqi_val), [(2, "safe"), (3, "moderate"), (4, "high"), (6, "critical")])
        overall_level = _aggregate_level([pm10_level, so2_level, aqi_level])

        forecast_points.append(
            {
                "timestamp": target_time.isoformat(timespec="minutes"),
                "aqi": aqi_val,
                "aqi_label": _aqi_label(aqi_val),
                "pm10": round(pm10_val, 2),
                "so2": round(so2_val, 2),
                "level": overall_level,
                "alert": _build_alert(overall_level),
            }
        )

    return forecast_points


def get_air_quality_summary(hours_ahead: int = 24, step_hours: int = 4) -> dict[str, Any]:
    rows = _load_rows()
    if not rows:
        return {
            "current": None,
            "forecast": [],
            "history": [],
            "model": {
                "type": "linear_regression",
                "window": 0,
                "step_hours": step_hours,
                "hours_ahead": hours_ahead,
                "metrics": {
                    "aqi": _regression_metrics([]),
                    "pm10": _regression_metrics([]),
                    "so2": _regression_metrics([]),
                },
            },
        }

    rows_sorted = sorted(rows, key=lambda row: row.get("timestamp", ""))
    window = rows_sorted[-48:] if len(rows_sorted) > 48 else rows_sorted
    history_rows = rows_sorted[-168:] if len(rows_sorted) > 168 else rows_sorted

    current = _build_current(rows_sorted[-1])
    forecast = _build_forecast(window, hours_ahead, step_hours)
    reasoning = _get_period_reasoning(rows_sorted, days=3)

    aqi_values = [float(_parse_int(row.get("aqi")) or 0) for row in window]
    pm10_values = [float(_parse_float(row.get("pm10")) or 0) for row in window]
    so2_values = [float(_parse_float(row.get("so2")) or 0) for row in window]

    overall_alert = current.get("alert") if current else None
    if forecast:
        forecast_peak = max(forecast, key=lambda item: LEVEL_ORDER.get(item.get("level", "unknown"), -1))
        if forecast_peak and LEVEL_ORDER.get(forecast_peak.get("level", "unknown"), -1) > LEVEL_ORDER.get(overall_alert.get("level", "unknown"), -1):
            overall_alert = forecast_peak.get("alert")

    return {
        "current": current,
        "forecast": forecast,
        "history": [
            {
                "timestamp": row.get("timestamp"),
                "aqi": _parse_int(row.get("aqi")),
                "pm10": _parse_float(row.get("pm10")),
                "so2": _parse_float(row.get("so2")),
            }
            for row in history_rows
        ],
        "overall_alert": overall_alert,
        "model": {
            "type": "linear_regression",
            "window": len(window),
            "step_hours": step_hours,
            "hours_ahead": hours_ahead,
            "metrics": {
                "aqi": _regression_metrics(aqi_values),
                "pm10": _regression_metrics(pm10_values),
                "so2": _regression_metrics(so2_values),
            },
        },
        "reasoning": reasoning,
    }
