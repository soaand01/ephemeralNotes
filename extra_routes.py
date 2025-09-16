from typing import Callable
from flask import render_template, request
import os
from redis import from_url as redis_from_url

def register(app) -> None:
    def _test_redis():
        result = None
        message = ""
        if request.method == 'POST':
            redis_url = os.getenv("REDIS_URL")
            try:
                r = redis_from_url(redis_url)
                r.ping()
                result = True
                message = "Successfully connected to Redis!"
            except Exception as e:
                result = False
                message = f"Failed to connect to Redis: {e}"
        return render_template('test_redis.html', result=result, message=message)

    app.add_url_rule('/test-redis', endpoint='test_redis', view_func=_test_redis, methods=['GET','POST'])
