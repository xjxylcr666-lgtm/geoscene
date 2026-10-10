import re
from datetime import UTC, datetime
from typing import Any


class GeoJsonConversionError(ValueError):
    pass


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _normalize(value: float, minimum: float, maximum: float, start: float, end: float) -> float:
    if maximum == minimum:
        return (start + end) / 2
    ratio = (value - minimum) / (maximum - minimum)
    return start + ratio * (end - start)


def _safe_id(value: str, index: int) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-")
    return f"quake-{cleaned or index + 1}"


def _color_for_magnitude(magnitude: float) -> str:
    if magnitude >= 7:
        return "#ff3344"
    if magnitude >= 6:
        return "#ff8c33"
    return "#ffd43b"


def convert_earthquake_geojson(data: Any, max_features: int = 12) -> dict[str, Any]:
    """Convert USGS-style point GeoJSON into GeoScene target configurations."""
    if not isinstance(data, dict) or data.get("type") != "FeatureCollection":
        raise GeoJsonConversionError("GeoJSON必须是FeatureCollection")

    features = data.get("features")
    if not isinstance(features, list) or not features:
        raise GeoJsonConversionError("GeoJSON必须包含至少一个feature")

    valid_features: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, feature in enumerate(features[:max_features]):
        if not isinstance(feature, dict):
            warnings.append(f"features[{index}]不是对象，已跳过")
            continue

        geometry = feature.get("geometry")
        properties = feature.get("properties")
        coordinates = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if (
            not isinstance(geometry, dict)
            or geometry.get("type") != "Point"
            or not isinstance(coordinates, list)
            or len(coordinates) < 3
            or not all(_is_number(value) for value in coordinates[:3])
            or not isinstance(properties, dict)
            or not _is_number(properties.get("mag"))
        ):
            warnings.append(f"features[{index}]缺少有效点坐标或震级，已跳过")
            continue

        valid_features.append(feature)

    if not valid_features:
        raise GeoJsonConversionError("没有可转换的地震点要素")

    longitudes = [feature["geometry"]["coordinates"][0] for feature in valid_features]
    latitudes = [feature["geometry"]["coordinates"][1] for feature in valid_features]
    lon_min, lon_max = min(longitudes), max(longitudes)
    lat_min, lat_max = min(latitudes), max(latitudes)

    targets: list[dict[str, Any]] = []
    for index, feature in enumerate(valid_features):
        longitude, latitude, depth_km = feature["geometry"]["coordinates"][:3]
        properties = feature["properties"]
        magnitude = float(properties["mag"])
        place = properties.get("place") or "未知地点"
        event_id = str(feature.get("id") or index + 1)
        height = round(0.7 + max(0, magnitude - 5) * 0.55, 3)
        event_time = properties.get("time")
        time_iso = None
        if _is_number(event_time):
            time_iso = datetime.fromtimestamp(event_time / 1000, tz=UTC).isoformat()

        targets.append(
            {
                "id": _safe_id(event_id, index),
                "name": f"M{magnitude:.1f} {place}",
                "type": "target",
                "position": {
                    "x": round(_normalize(longitude, lon_min, lon_max, -3.5, 6.0), 3),
                    "y": round(height / 2, 3),
                    "z": round(_normalize(latitude, lat_min, lat_max, -3.0, 3.0), 3),
                },
                "size": {
                    "width": round(0.45 + max(0, magnitude - 5) * 0.12, 3),
                    "height": height,
                    "depth": round(0.45 + max(0, magnitude - 5) * 0.12, 3),
                },
                "color": _color_for_magnitude(magnitude),
                "sourceData": {
                    "provider": "USGS",
                    "eventId": event_id,
                    "magnitude": magnitude,
                    "longitude": longitude,
                    "latitude": latitude,
                    "depthKm": depth_km,
                    "time": time_iso,
                    "url": properties.get("url"),
                },
            }
        )

    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    return {
        "targets": targets,
        "warnings": warnings,
        "metadata": {
            "provider": "USGS Earthquake Hazards Program",
            "title": metadata.get("title") or "USGS Earthquakes",
            "count": len(targets),
            "geographicExtent": {
                "minLongitude": lon_min,
                "maxLongitude": lon_max,
                "minLatitude": lat_min,
                "maxLatitude": lat_max,
            },
            "coordinateMode": "normalized_geographic_demo",
            "coordinateNote": "经纬度已线性归一化到Three.js本地演示坐标；场景距离不代表真实地理距离。",
        },
    }
