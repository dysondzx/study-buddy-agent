# 学习笔记

## RAG 核心流程

RAG（检索增强生成）核心流程：文档切块 → 向量化 → 存入向量库 → 相似度检索 → 喂给 LLM 生成答案。

## 混合检索

向量检索擅长语义匹配，不擅长精确字面匹配；BM25 擅长精确匹配。混合检索结合两者，用 RRF 融合。

## RAGAS 评估指标

RAGAS 评估指标：Faithfulness 衡量答案是否被上下文支持；AnswerRelevancy 衡量是否解决问题；ContextRecall 衡量召回率。

## LangGraph 多 Agent 编排

LangGraph 用状态图编排多 Agent：add_node 加节点，add_conditional_edges 做条件路由。

## Rerank 重排

Rerank 用 Cross-Encoder 对召回的候选集精排，只能在已召回的候选里重排，召回率是它的天花板。
