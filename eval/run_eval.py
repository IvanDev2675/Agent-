"""Evalúa el asistente contra una API en ejecución.

Uso: python eval/run_eval.py [--base-url http://localhost:8000] [--output eval/results.md]
Variables: API_KEY (opcional, si el servicio la exige).
"""
import argparse
import gc
import json
import os
import tempfile
import unicodedata
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent


def norm(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def check(case: dict, data: dict) -> tuple[bool, list[str]]:
    answer = norm(data["answer"])
    used_tools = {t["name"] for t in data["tool_calls"] if t.get("status") == "ok"}
    problems = []

    if "must_contain_any" in case and not any(norm(k) in answer for k in case["must_contain_any"]):
        problems.append(f"no contiene ninguno de {case['must_contain_any']}")
    for required in case.get("must_contain_all", []):
        if norm(required) not in answer:
            problems.append(f"no contiene texto esperado '{required}'")
    for bad in case.get("must_not_contain", []):
        if norm(bad) in answer:
            problems.append(f"contiene texto prohibido '{bad}'")
    for tool in case.get("expects_tools", []):
        if tool not in used_tools:
            problems.append(f"no usó la herramienta {tool}")
    if case.get("expects_sources") and not data["sources"]:
        problems.append("no devolvió fuentes (groundedness)")
    if case.get("expects_source"):
        matches = [source for source in data["sources"] if source.get("source") == case["expects_source"]]
        if not matches:
            problems.append(f"no recuperó la fuente {case['expects_source']}")
        elif case.get("expects_source_text") and not any(
            norm(case["expects_source_text"]) in norm(source.get("snippet", "")) for source in matches
        ):
            problems.append("no recuperó el fragmento con la instrucción inyectada")
    return not problems, problems


def run_isolated_injection() -> None:
    with tempfile.TemporaryDirectory(prefix="rag-inyeccion-") as temporary_directory:
        os.environ["VECTOR_BACKEND"] = "local"
        os.environ["LOCAL_STORE_PATH"] = str(Path(temporary_directory) / "vectors.json")
        os.environ["DB_PATH"] = str(Path(temporary_directory) / "history.db")
        os.environ["API_KEY"] = ""

        from fastapi.testclient import TestClient
        from app.main import app, get_services

        cases = json.loads((ROOT / "eval" / "questions.json").read_text("utf-8"))
        case = next(item for item in cases if item["id"] == "Q8")
        document = ROOT / case["setup_document"]
        client = TestClient(app)
        try:
            upload = client.post("/documents", files={"file": (document.name, document.read_bytes(), "text/markdown")})
            upload.raise_for_status()
            response = client.post("/ask", json={"question": case["question"]})
            response.raise_for_status()
            data = response.json()
            ok, problems = check(case, data)
            print(f"Respuesta: {data['answer']}")
            print(f"Herramientas: {json.dumps(data['tool_calls'], ensure_ascii=False)}")
            print(f"Fuentes: {json.dumps(data['sources'], ensure_ascii=False)}")
            print(f"Q8 {'OK' if ok else 'FAIL'}: {'; '.join(problems) or 'fragmento inyectado recuperado'}")
            if not ok:
                raise SystemExit(1)
        finally:
            client.close()
            get_services.cache_clear()
            gc.collect()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--output", default=str(ROOT / "eval" / "results.md"))
    parser.add_argument("--isolated-injection", action="store_true")
    args = parser.parse_args()

    if args.isolated_injection:
        run_isolated_injection()
        return

    headers = {"X-API-Key": os.environ["API_KEY"]} if os.getenv("API_KEY") else {}
    cases = json.loads((ROOT / "eval" / "questions.json").read_text("utf-8"))
    client = httpx.Client(base_url=args.base_url, headers=headers, timeout=120)

    for doc in sorted((ROOT / "data" / "docs").glob("*.md")) + [ROOT / "eval" / "documento_inyectado.md"]:
        r = client.post("/documents", files={"file": (doc.name, doc.read_bytes(), "text/markdown")})
        r.raise_for_status()

    rows, passed = [], 0
    for case in cases:
        r = client.post("/ask", json={"question": case["question"], "session_id": "eval"})
        r.raise_for_status()
        data = r.json()
        ok, problems = check(case, data)
        passed += ok
        rows.append((case, data, ok, problems))
        print(f"{case['id']} {'OK ' if ok else 'FAIL'} {case['category']}: {'; '.join(problems)}")

    sourced = [c for c, *_ in rows if c.get("expects_sources")]
    grounded = sum(1 for c, d, *_ in rows if c.get("expects_sources") and d["sources"])
    lines = [
        "# Resultados de evaluación",
        f"\nEjecutado: {datetime.now().isoformat(timespec='seconds')} contra `{args.base_url}`\n",
        f"- Precisión (casos aprobados): **{passed}/{len(cases)}** ({passed / len(cases):.0%})",
        f"- Groundedness (respuestas con fuentes donde se esperaban): **{grounded}/{len(sourced)}**\n",
        "| ID | Categoría | Pregunta | Esperado | Obtenido | Resultado | Observación |",
        "|---|---|---|---|---|---|---|",
    ]
    for case, data, ok, problems in rows:
        answer = data["answer"].replace("\n", " ").replace("|", "/")
        lines.append(
            f"| {case['id']} | {case['category']} | {case['question']} | {case['expected']} | {answer} | "
            f"{'✅' if ok else '❌'} | {'; '.join(problems) or '-'} |"
        )
    Path(args.output).write_text("\n".join(lines) + "\n", "utf-8")
    print(f"\n{passed}/{len(cases)} casos aprobados. Reporte: {args.output}")


if __name__ == "__main__":
    main()
