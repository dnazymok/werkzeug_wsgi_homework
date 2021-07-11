import json
import os
from datetime import datetime


from werkzeug.serving import run_simple
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.shared_data import SharedDataMiddleware
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader


class BulletinBoard(object):

    def __init__(self):
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                     autoescape=True)
        self.url_map = Map([
            Rule('/', endpoint='posts'),
            Rule('/create_post', endpoint='create_post'),
            Rule('/posts/<id>', endpoint='show_post')
        ])

    def on_posts(self, request):
        with open("database.json", 'r', encoding="utf-8") as f:
            posts = json.load(f)
            posts.sort(key=lambda x: x["date"], reverse=True)
        return self.render_template("index.html", posts=posts)

    def on_create_post(self, request):
        if request.method == "POST" and self.is_request_form_valid(request):
            self.create_new_post(request)
            return redirect("/")
        return self.render_template("create_post.html")

    def on_show_post(self, request, id):
        if request.method == "POST":
            self._add_comment(request, id)
        with open("database.json", "r") as file:
            file_data = json.load(file)
        for i in file_data:
            if i["id"] == int(id):
                post = i
        return self.render_template("show_post.html", post=post)

    def create_new_post(self, request):
        data = {}
        data["id"] = self._get_id_for_next_post()
        data["author"] = request.form["author"]
        data["title"] = request.form["title"]
        data["text"] = request.form["text"]
        data["date"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        data["comments"] = []
        with open("database.json", "r") as file:
            file_data = json.load(file)
        file_data.append(data)
        with open("database.json", "w") as file:
            json.dump(file_data, file)

    def _add_comment(self, request, post_id):
        data = {}
        data["text"] = request.form["text"]
        data["author"] = request.form["author"]
        with open("database.json", "r") as file:
            file_data = json.load(file)
        for i in file_data:
            if i["id"] == int(post_id):
                i["comments"].append(data)
        with open("database.json", "w") as file:
            json.dump(file_data, file)

    def _get_id_for_next_post(self):
        with open("database.json", "r") as file:
            file_data = json.load(file)
            try:
                last_item = file_data.pop()
            except IndexError:
                return 1
            return last_item["id"] + 1

    def is_request_form_valid(self, request):
        return request.form["author"] and request.form["title"] and \
               request.form["text"]

    def dispatch_request(self, request):
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()
            return getattr(self, f'on_{endpoint}')(request, **values)
        except HTTPException as e:
            return e

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

    def render_template(self, template_name, **context):
        template = self.jinja_env.get_template(template_name)
        return Response(template.render(context), mimetype='text/html')


def create_app(with_static=True):
    app = BulletinBoard()
    if with_static:
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static': os.path.join(os.path.dirname(__file__), 'static')
        })
    return app


if __name__ == '__main__':
    app = create_app()
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
