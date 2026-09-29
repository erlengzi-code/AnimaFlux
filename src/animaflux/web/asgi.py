"""uvicorn 入口（§Web Plan §39.21 / §39.22）：`uvicorn animaflux.web.asgi:app`。"""

from animaflux.web.app import create_app

app = create_app()
