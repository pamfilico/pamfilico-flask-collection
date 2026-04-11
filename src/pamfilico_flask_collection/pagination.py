"""Pagination decorator for Flask API endpoints."""

from functools import wraps

from flask import request

from pamfilico_flask_core.errors import ServerError
from pamfilico_flask_core.responses import standard_response


def collection(MarshmallowSchema, searchable_fields=None, sortable_fields=None):
    """
    Decorator that automatically paginates SQLAlchemy query results with optional search and sorting.

    Uses standard_response and raises ValueError for validation errors (handled by init_errors).
    Pagination/ordering keys follow docs spec (camelCase).

    Args:
        MarshmallowSchema: A Marshmallow schema class for serialization
        searchable_fields (list): List of field names that can be searched
        sortable_fields (list): List of field names that can be sorted

    Returns:
        standard_response with data, pagination (camelCase), ordering when applicable
    """
    searchable_fields = searchable_fields or []
    sortable_fields = sortable_fields or []

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = kwargs.get("auth")

            try:
                results_per_page = int(request.args.get("results_per_page", 10))
                page_number = int(request.args.get("page_number", 1))
            except ValueError:
                raise ValueError("Invalid pagination parameters. Must be integers.")

            search_by = request.args.get("search_by", "").strip()
            search_value = request.args.get("search_value", "").strip()
            order_by = request.args.get("order_by", "").strip()
            order_direction = request.args.get("order_direction", "asc").strip().lower()

            if search_by and search_by not in searchable_fields:
                raise ValueError(
                    f"Invalid search field. Allowed fields: {', '.join(searchable_fields)}"
                )

            if order_by and order_by not in sortable_fields:
                raise ValueError(
                    f"Invalid sort field. Allowed fields: {', '.join(sortable_fields)}"
                )

            if order_direction not in ["asc", "desc"]:
                raise ValueError("order_direction must be 'asc' or 'desc'")

            if results_per_page < 1 or results_per_page > 100:
                raise ValueError("results_per_page must be between 1 and 100")

            if page_number < 1:
                raise ValueError("page_number must be greater than 0")

            session = None
            try:
                query = f(*args, **kwargs)
                model_class = query.column_descriptions[0]["type"]

                if search_by and search_value:
                    if hasattr(model_class, search_by):
                        column = getattr(model_class, search_by)
                        query = query.filter(column.ilike(f"%{search_value}%"))
                    else:
                        raise ValueError(f"Field '{search_by}' not found in model")

                if order_by:
                    if hasattr(model_class, order_by):
                        column = getattr(model_class, order_by)
                        if order_direction == "desc":
                            query = query.order_by(column.desc())
                        else:
                            query = query.order_by(column.asc())
                    else:
                        raise ValueError(f"Field '{order_by}' not found in model")

                offset = (page_number - 1) * results_per_page
                total_count = query.count()
                paginated_query = query.limit(results_per_page).offset(offset)
                results = paginated_query.all()
                session = query.session
                schema = MarshmallowSchema(many=True)
                serialized_data = schema.dump(results)

            except (ValueError, ServerError):
                raise
            except Exception as e:
                if session:
                    try:
                        session.rollback()
                        session.close()
                    except Exception:
                        pass
                raise ServerError(f"Database error: {str(e)}", session=None)

            finally:
                if session:
                    session.close()

            total_pages = (total_count + results_per_page - 1) // results_per_page
            pagination_meta = {
                "currentPage": page_number,
                "totalPages": total_pages,
                "pageSize": results_per_page,
                "totalCount": total_count,
                "nextPage": page_number + 1 if page_number < total_pages else None,
                "previousPage": page_number - 1 if page_number > 1 else None,
            }
            ordering_meta = None
            if order_by:
                ordering_meta = {
                    "sortBy": order_by,
                    "sortOrder": order_direction,
                }

            return standard_response(
                data=serialized_data,
                pagination=pagination_meta,
                ordering=ordering_meta,
                status_code=200,
            )

        return wrapper

    return decorator
