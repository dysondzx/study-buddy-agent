from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    AnswerCorrectness,
)
from app.agents.orchestrator import build_graph
from app.evaluation import EvalSample, get_judge_llm, get_judge_embeddings


async def _run_graph(user_input: str) -> str:
    """复用编排中枢跑出最终答案（离线批处理，拼接 synthesizer 的流式输出）"""
    graph = build_graph()
    parts = []
    async for chunk, metadata in graph.astream(
        {"user_input": user_input}, stream_mode="messages"
    ):
        if metadata.get("langgraph_node") == "synthesizer" and chunk.content:
            parts.append(chunk.content)
    return "".join(parts)


async def evaluate_sample(sample: EvalSample, llm, embeddings,
                          metrics_config: dict) -> dict:
    response = await _run_graph(sample.user_input)
    sample.response = response

    faithfulness = Faithfulness(llm=llm) if metrics_config.get("faithfulness") else None
    answer_relevancy = AnswerRelevancy(llm=llm, embeddings=embeddings) if metrics_config.get("answer_relevancy") else None
    context_precision = ContextPrecision(llm=llm) if metrics_config.get("context_precision") else None
    context_recall = ContextRecall(llm=llm) if metrics_config.get("context_recall") else None
    answer_correctness = AnswerCorrectness(llm=llm) if metrics_config.get("answer_correctness") else None

    scores = {k: 0.0 for k in ["faithfulness", "answer_relevancy",
                                "context_precision", "context_recall", "answer_correctness"]}

    if faithfulness:
        try:
            r = await faithfulness.ascore(user_input=sample.user_input, response=sample.response)
            scores["faithfulness"] = r.value
        except Exception as e:
            print(f"  [WARN] Faithfulness 失败: {e}")

    if answer_relevancy:
        try:
            r = await answer_relevancy.ascore(user_input=sample.user_input, response=sample.response)
            scores["answer_relevancy"] = r.value
        except Exception as e:
            print(f"  [WARN] AnswerRelevancy 失败: {e}")

    if sample.reference:
        if context_precision:
            try:
                r = await context_precision.ascore(
                    user_input=sample.user_input, response=sample.response,
                    reference=sample.reference)
                scores["context_precision"] = r.value
            except Exception as e:
                print(f"  [WARN] ContextPrecision 失败: {e}")
        if context_recall:
            try:
                r = await context_recall.ascore(
                    user_input=sample.user_input, response=sample.response,
                    reference=sample.reference)
                scores["context_recall"] = r.value
            except Exception as e:
                print(f"  [WARN] ContextRecall 失败: {e}")
        if answer_correctness:
            try:
                r = await answer_correctness.ascore(
                    user_input=sample.user_input, response=sample.response,
                    reference=sample.reference)
                scores["answer_correctness"] = r.value
            except Exception as e:
                print(f"  [WARN] AnswerCorrectness 失败: {e}")

    return {"user_input": sample.user_input, "response": sample.response, **scores}


async def run_evaluation(dataset: list[EvalSample], metrics_config: dict) -> list[dict]:
    llm = get_judge_llm()
    embeddings = get_judge_embeddings()
    results = []
    for i, s in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] 评估: {s.user_input}")
        r = await evaluate_sample(s, llm, embeddings, metrics_config)
        results.append(r)
        print(f"    Faithfulness={r['faithfulness']:.3f}  AnswerRelevancy={r['answer_relevancy']:.3f}")
    print("\n===== 汇总 =====")
    n = len(results)
    for k in scores_keys():
        avg = sum(r[k] for r in results) / n if n else 0
        print(f"  平均 {k:20s}: {avg:.4f}")
    return results


def scores_keys():
    return ["faithfulness", "answer_relevancy", "context_precision", "context_recall", "answer_correctness"]
