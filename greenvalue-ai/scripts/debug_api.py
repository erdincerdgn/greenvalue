"""Debug: inspect Unstructured API response format."""
import httpx, io, json
from PyPDF2 import PdfReader, PdfWriter

# Extract 5 pages
r = PdfReader("/app/infrastructure/qdrant/knowledge_base/books/IVS-Jan-2025.pdf")
w = PdfWriter()
for i in range(5):
    w.add_page(r.pages[i])
buf = io.BytesIO()
w.write(buf)

# Send to API
resp = httpx.post(
    "http://greenvalue-unstructured:8000/general/v0/general",
    files={"files": ("test.pdf", io.BytesIO(buf.getvalue()), "application/pdf")},
    data={"strategy": "hi_res", "pdf_infer_table_structure": "true"},
    timeout=120,
)

print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Response type: {type(data)}")
print(f"Count: {len(data)}")

if data and isinstance(data, list):
    # Check first element
    first = data[0]
    print(f"First element type: {type(first)}")
    if isinstance(first, dict):
        print(f"Keys: {first.keys()}")
        print(f"Type field: {first.get('type')}")
        print(f"Text preview: {first.get('text', '')[:100]}")
    elif isinstance(first, str):
        print(f"String element: {first[:200]}")
    
    # Count types
    types = {}
    for elem in data:
        if isinstance(elem, dict):
            t = elem.get("type", "unknown")
        else:
            t = type(elem).__name__
        types[t] = types.get(t, 0) + 1
    print(f"Element types: {types}")
