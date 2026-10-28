"""
route_service.py
----------------
NOTE ON THE NAME: this file manages BUS ROUTES (Mumbai -> Virar, the
`routes` table). It has nothing to do with Flask's `@app.route(...)`
URL routing - deciding which Python function handles /api/login vs
/api/signup is done in app.py. Two different meanings of the word
"route"; this file is about the bus, not the web request.
(It was called routes.py in the http.server version; renamed to avoid
confusion now that Flask has "routes" of its own.)

This is the "service layer" for the admin's route-management screen:
add a route, list all routes, list only active ones, toggle a route
active/inactive, and stop obvious duplicates.
"""

import models


def add_route(db, from_city, to_city, active):
    from_city = from_city.strip()
    to_city = to_city.strip()

    if not from_city or not to_city:
        return False, "From and To cities are required", None

    if from_city.lower() == to_city.lower():
        return False, "From and To cannot be the same city", None

    if models.Route.exists(db, from_city, to_city):
        return False, "This route already exists", None

    route_id = models.Route.create(db, from_city, to_city, active)
    return True, "Route added successfully", route_id


def list_routes(db):
    return models.Route.list_all(db)


def list_active_routes(db):
    """Students should only ever see these when applying for a pass."""
    return models.Route.list_active(db)


def set_route_active(db, route_id, active):
    route = models.Route.find_by_id(db, route_id)
    if not route:
        return False, "Route not found"

    models.Route.set_active(db, route_id, active)
    state = "activated" if active else "deactivated"
    return True, f"Route {state} successfully"
