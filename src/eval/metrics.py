# eval/metrics.py
"""Metricas de recuperacion. `ranked` = lista ordenada de doc_id; `rel` = {doc_id: relevancia (1 o 2)}."""
import math
from typing import Dict, List


def hit_at_k(ranked: List[str], rel: Dict[str, int], k: int) -> float:
    return float(any(d in rel for d in ranked[:k]))


def recall_at_k(ranked: List[str], rel: Dict[str, int], k: int) -> float:
    return len({d for d in ranked[:k] if d in rel}) / len(rel) if rel else 0.0


def precision_at_k(ranked: List[str], rel: Dict[str, int], k: int) -> float:
    # denominador fijo k: devolver menos de k documentos no se premia
    return sum(1 for d in ranked[:k] if d in rel) / k


def mrr(ranked: List[str], rel: Dict[str, int]) -> float:
    for i, d in enumerate(ranked, 1):
        if d in rel:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: List[str], rel: Dict[str, int], k: int) -> float:
    dcg = sum((2 ** rel.get(d, 0) - 1) / math.log2(i + 1) for i, d in enumerate(ranked[:k], 1))
    ideal = sorted(rel.values(), reverse=True)[:k]
    idcg = sum((2 ** r - 1) / math.log2(i + 1) for i, r in enumerate(ideal, 1))
    return dcg / idcg if idcg else 0.0


def fuentes_distintas(ranked: List[str], k: int) -> int:
    """Diversidad: cuantas fuentes distintas aparecen en el top-k (cf. METRICAS_EFECTIVIDAD 5.1)."""
    return len({d.split(":", 1)[0] for d in ranked[:k]})


def mrr_objetivo(ranked: List[str], rel: Dict[str, int]) -> float:
    """MRR solo sobre los items de relevancia maxima (2): p. ej. el desempeno del grado correcto."""
    return mrr(ranked, {d: r for d, r in rel.items() if r >= 2})


def evaluar(ranked: List[str], rel: Dict[str, int], ks=(3, 5, 10)) -> Dict[str, float]:
    out = {"mrr": mrr(ranked, rel), "mrr_obj": mrr_objetivo(ranked, rel)}
    obj = {d: r for d, r in rel.items() if r >= 2}
    for k in (1, 3, 5):
        out[f"hit_obj@{k}"] = hit_at_k(ranked, obj, k)
    for k in ks:
        out[f"hit@{k}"] = hit_at_k(ranked, rel, k)
        out[f"recall@{k}"] = recall_at_k(ranked, rel, k)
        out[f"precision@{k}"] = precision_at_k(ranked, rel, k)
        out[f"ndcg@{k}"] = ndcg_at_k(ranked, rel, k)
    out["fuentes@5"] = fuentes_distintas(ranked, 5)
    return out
