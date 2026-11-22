def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    """Divide el texto por párrafos y agrupa hasta `size` caracteres, con solape entre chunks."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Parámetros de chunking inválidos")

    paragraphs = [p.strip() for p in text.replace("\r\n", "\n").split("\n\n") if p.strip()]
    pieces: list[str] = []
    for p in paragraphs:
        # un párrafo más largo que `size` se corta con ventana deslizante
        if len(p) <= size:
            pieces.append(p)
        else:
            step = size - overlap
            pieces.extend(p[i : i + size] for i in range(0, len(p), step))

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) + 2 > size:
            chunks.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n\n{piece}" if tail else piece
        else:
            current = f"{current}\n\n{piece}" if current else piece
    if current:
        chunks.append(current)
    return chunks
