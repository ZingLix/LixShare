from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from Util.db import doc_db
from pydantic import BaseModel
from enum import Enum
import time
import uuid
import markdown
import datetime
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# https://stackoverflow.com/questions/1119722/base-62-conversion
BASE62 = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def encode(num, alphabet):
    """Encode a positive number into Base X and return the string.

    Arguments:
    - `num`: The number to encode
    - `alphabet`: The alphabet to use for encoding
    """
    if num == 0:
        return alphabet[0]
    arr = []
    arr_append = arr.append  # Extract bound-method for faster access.
    _divmod = divmod  # Access to locals is faster.
    base = len(alphabet)
    while num:
        num, rem = _divmod(num, base)
        arr_append(alphabet[rem])
    arr.reverse()
    return "".join(arr)


def generate_id(length=10):
    return encode(uuid.uuid4().int, BASE62)[:length]


class DocumentType(Enum):
    Markdown = "markdown"
    HTML = "html"


class CreateDocumentRequest(BaseModel):
    doc_type: DocumentType
    title: Optional[str]
    content: str
    expire: int


app = FastAPI()
app.mount("/css", StaticFiles(directory="static/css"), name="css")
app.mount("/js", StaticFiles(directory="static/js"), name="js")
app.mount("/fonts", StaticFiles(directory="static/fonts"), name="fonts")

templates = Jinja2Templates(directory="template")


@app.post("/")
async def create_document(req: CreateDocumentRequest):
    id = generate_id()
    retry = 0
    while doc_db.find_one({"doc_id": id}) != None:
        id = generate_id()
        retry += 1
        if retry > 10:
            raise HTTPException(
                status_code=400, detail="seems keys temporarily available"
            )
    content = req.content
    if req.doc_type == DocumentType.Markdown:
        content = markdown.markdown(content)
    if req.expire == -1:
        expire_at = 0
    else:
        expire_at = int(time.time()) + req.expire
    doc_db.insert_one(
        {"doc_id": id, "content": content, "title": req.title, "expire_at": expire_at}
    )
    return {"url": "/" + id}


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/{doc_id}")
async def get_document(request: Request, doc_id: str):
    item = doc_db.find_one({"doc_id": doc_id})
    if item != None and item["expire_at"] != 0 and item["expire_at"] < time.time():
        item = None
        doc_db.delete_many({"doc_id": doc_id})
    if item is None:
        return templates.TemplateResponse(
            "doc.html",
            {"request": request, "title": "文档不存在或已过期", "expire_at": None},
        )
    return templates.TemplateResponse(
        "doc.html",
        {
            "request": request,
            "title": item["title"],
            "expire_at": time.strftime(
                "%Y-%m-%d %H:%M:%S", time.localtime(item["expire_at"])
            )
            if item["expire_at"] != 0
            else "Never",
            "content": item["content"],
        },
    )
