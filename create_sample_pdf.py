"""
create_sample_pdf.py — Generate sample/sample.pdf using Python stdlib only.

Run once before testing:
    python create_sample_pdf.py

No external dependencies required.
"""
import os


def make_pdf(output_path: str) -> None:
    """Write a minimal but valid single-page PDF to output_path."""

    # PDF objects as byte strings
    obj1 = b"<< /Type /Catalog /Pages 2 0 R >>"
    obj2 = b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>"
    obj3 = (
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 "
        b"/BaseFont /Helvetica >> >> >> >>"
    )

    objects = {1: obj1, 2: obj2, 3: obj3}

    body = b"%PDF-1.4\n"
    offsets: dict[int, int] = {}

    for num in sorted(objects):
        offsets[num] = len(body)
        body += f"{num} 0 obj\n".encode()
        body += objects[num] + b"\n"
        body += b"endobj\n"

    xref_offset = len(body)
    total_objects = max(objects) + 1  # objects 0 .. max

    body += b"xref\n"
    body += f"0 {total_objects}\n".encode()
    body += b"0000000000 65535 f \n"   # object 0 — always free

    for i in range(1, total_objects):
        if i in offsets:
            body += f"{offsets[i]:010d} 00000 n \n".encode()
        else:
            body += b"0000000000 65535 f \n"

    body += b"trailer\n"
    body += f"<< /Size {total_objects} /Root 1 0 R >>\n".encode()
    body += b"startxref\n"
    body += str(xref_offset).encode() + b"\n"
    body += b"%%EOF\n"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as fh:
        fh.write(body)

    print(f"Created: {output_path}  ({len(body)} bytes)")


if __name__ == "__main__":
    make_pdf("sample/sample.pdf")
