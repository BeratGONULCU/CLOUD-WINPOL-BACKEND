from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.init_master import init_master_db
from app.routers import auth, companies,tenantdb,mikro_test,mikro_api

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_master_db()
    yield

app = FastAPI(
    title="Winpol SaaS Backend",
    version="1.0.0",
    lifespan=lifespan
)

# BU BLOK OLMAZSA FLUTTER WEB ÇALIŞMAZ
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://37.27.204.97:8080",
        "http://37.27.204.97",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(tenantdb.router)
app.include_router(mikro_test.router)
