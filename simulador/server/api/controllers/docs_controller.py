"""API documentation: the OpenAPI document and a Swagger UI page to browse and try it."""

from string import Template

from flask import Blueprint, Response, jsonify, redirect, url_for

from api.controllers.openapi import openapi_spec

bp = Blueprint("docs", __name__)

# Swagger UI is loaded from jsDelivr, pinned and with Subresource Integrity, so a
# changed file is refused by the browser. Bumping the version means new hashes:
#   curl -s <url> | openssl dgst -sha384 -binary | openssl base64 -A
SWAGGER_UI_VERSION = "5.35.0"
_CDN = f"https://cdn.jsdelivr.net/npm/swagger-ui-dist@{SWAGGER_UI_VERSION}"
_JS_INTEGRITY = "sha384-gjRm0bEPMeTmMh5jT2cHccIwCUZSTd8YC+j0d0sXw0MdGEfScduGpSyF3ZSSLkX9"
_CSS_INTEGRITY = "sha384-WlYgdmXYOOBWL5apwjDEZwN+U3HmXSSu5R6V5aGxEcf7z+KuRNwBhoxKVN1i3D5I"

_PAGE = Template("""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Simulador de Campeonato · API</title>
  <link rel="stylesheet" href="$cdn/swagger-ui.css" integrity="$css_integrity" crossorigin="anonymous">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="$cdn/swagger-ui-bundle.js" integrity="$js_integrity" crossorigin="anonymous"></script>
  <script>
    SwaggerUIBundle({
      url: "$spec_url",
      dom_id: "#swagger-ui",
      deepLinking: true,
      displayRequestDuration: true,
    });
  </script>
</body>
</html>
""")


@bp.get("/openapi.json")
def openapi():
    return jsonify(openapi_spec())


@bp.get("/docs")
def swagger_ui():
    page = _PAGE.substitute(
        cdn=_CDN,
        js_integrity=_JS_INTEGRITY,
        css_integrity=_CSS_INTEGRITY,
        spec_url=url_for("docs.openapi"),
    )
    return Response(page, mimetype="text/html")


@bp.get("/")
def index():
    return redirect(url_for("docs.swagger_ui"))
