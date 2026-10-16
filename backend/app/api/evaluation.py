"""RAGAS 评估的 HTTP 接口（原 app/evaluation/api.py）。"""
import asyncio
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.evaluation import DEFAULT_DATASET
from app.evaluation.runner import run_evaluation, scores_keys

router = APIRouter()
_TASKS: dict[str, dict] = {}


class EvalRequest(BaseModel):
    limit: int = 0
    metrics: list[str] = list(scores_keys())


async def _run_task(task_id, dataset, cfg):
    try:
        _TASKS[task_id]["status"] = "running"
        results = await run_evaluation(dataset, cfg)
        _TASKS[task_id].update(status="success", total=len(results), results=results)
    except Exception as e:
        _TASKS[task_id].update(status="failed", error=str(e))


@router.get("/api/eval/health")
async def health():
    return {
        "status": "ok",
        "dataset_size": len(DEFAULT_DATASET),
        "running": sum(1 for t in _TASKS.values() if t["status"] == "running"),
    }


@router.post("/api/eval/run")
async def start_eval(req: EvalRequest):
    unknown = set(req.metrics) - set(scores_keys())
    if unknown:
        raise HTTPException(400, f"未知指标: {sorted(unknown)}")
    cfg = {k: (k in req.metrics) for k in scores_keys()}
    dataset = DEFAULT_DATASET if req.limit <= 0 else DEFAULT_DATASET[:req.limit]
    task_id = str(uuid.uuid4())
    _TASKS[task_id] = {"status": "pending", "total": 0, "results": None, "error": None}
    asyncio.create_task(_run_task(task_id, dataset, cfg))
    return {"task_id": task_id, "status": "pending", "dataset_size": len(dataset)}


@router.get("/api/eval/run/{task_id}")
async def get_result(task_id: str):
    task = _TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "task_id 不存在")
    resp = {"task_id": task_id, "status": task["status"]}
    if task["status"] == "success":
        resp["total"] = task["total"]
        resp["results"] = task["results"]
    elif task["status"] == "failed":
        resp["error"] = task["error"]
    return resp
