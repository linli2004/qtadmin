from fastapi import FastAPI

app = FastAPI(title="QuantTide Finance Toolkit")


@app.get("/health")
def health():
    return {"status": "ok"}
