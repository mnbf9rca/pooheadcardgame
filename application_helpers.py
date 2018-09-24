import requests
import urllib.parse

from flask import redirect, render_template, request, session, make_response
from functools import wraps


def admin_user_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        elif session.get("is_admin"):
            return f(*args, **kwargs)
        else:
            return make_response("you are not authorized to view this page", 401)

    return decorated_function