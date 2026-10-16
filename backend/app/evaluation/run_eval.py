import argparse
import asyncio
from app.evaluation import DEFAULT_DATASET
from app.evaluation.runner import run_evaluation, scores_keys

DEFAULT_METRICS = "faithfulness,answer_relevancy,context_precision,context_recall,answer_correctness"


def parse_args():
    p = argparse.ArgumentParser(description="学伴智能体助手 RAGAS 评估")
    p.add_argument("--metrics", type=str, default=DEFAULT_METRICS, help="启用的指标，逗号分隔")
    p.add_argument("--limit", type=int, default=0, help="只评估前 N 条（0 为全部）")
    return p.parse_args()


def main():
    args = parse_args()
    enabled = {m.strip() for m in args.metrics.split(",") if m.strip()}
    cfg = {k: (k in enabled) for k in scores_keys()}
    dataset = DEFAULT_DATASET if args.limit <= 0 else DEFAULT_DATASET[:args.limit]
    print(f"待评估样本数: {len(dataset)}  启用: {[k for k,v in cfg.items() if v]}\n")
    asyncio.run(run_evaluation(dataset, cfg))
    print("评估完成。")


if __name__ == "__main__":
    main()
