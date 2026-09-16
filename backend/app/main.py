from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router
from .database import Base, engine, settings

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Smart Helpdesk API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(router)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
	app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="frontend-assets")

	@app.get("/", include_in_schema=False)
	def frontend_root() -> FileResponse:
		return FileResponse(frontend_dist / "index.html")

	@app.get("/{path:path}", include_in_schema=False)
	def frontend_route(path: str) -> FileResponse:
		return FileResponse(frontend_dist / "index.html")
else:

	@app.get("/")
	def root() -> dict[str, str]:
		return {"name": "Smartdesk API", "docs": "/docs", "health": "/api/health"}
