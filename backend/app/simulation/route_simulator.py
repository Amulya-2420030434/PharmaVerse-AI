from __future__ import annotations

from datetime import datetime, timedelta

from .models import RoutePoint


class RouteSimulator:
    def generate_route(self, origin: str, destination: str, points: list[tuple[float, float, str]] | None = None) -> list[RoutePoint]:
        if points is None:
            points = [
                (12.9716, 77.5946, "Bengaluru"),
                (13.0674, 77.1200, "Mysuru"),
                (12.2958, 76.6394, "Coimbatore"),
                (13.0827, 80.2707, "Chennai"),
            ]

        route: list[RoutePoint] = []
        current = datetime.utcnow()
        for index, (lat, lon, name) in enumerate(points):
            route.append(
                RoutePoint(
                    latitude=lat,
                    longitude=lon,
                    location_name=name,
                    timestamp=current + timedelta(hours=index),
                )
            )
        return route
