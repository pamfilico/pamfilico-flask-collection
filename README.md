# pamfilico-flask-collection

Collection decorator with pagination, search, sorting, and filtering for Flask + SQLAlchemy APIs.

Depends on [`pamfilico-flask-core`](../flask-core) for `standard_response` and error classes.

## Installation

```bash
pip install git+https://github.com/pamfilico/pamfilico-flask-collection.git
```

## Usage

### Collection decorator

Wraps a route that returns a SQLAlchemy query and automatically handles pagination, search, and sorting:

```python
from pamfilico_flask_collection import collection

@app.route('/api/vehicles')
@collection(
    VehicleGetSchema,
    searchable_fields=['name', 'license_plate'],
    sortable_fields=['name', 'created_at'],
)
def list_vehicles(auth):
    return session.query(Vehicle).filter_by(user_id=auth['id'])
```

Query parameters: `results_per_page`, `page_number`, `search_by`, `search_value`, `order_by`, `order_direction`.

### Filtering

Apply `filter[field][operator]=value` query params to SQLAlchemy queries:

```python
from pamfilico_flask_collection import apply_filters

query = session.query(Vehicle)
query, active_filters = apply_filters(query, Vehicle, request.args, allowed_fields={'status', 'price'})
```

Supported operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `contains`, `in`.
