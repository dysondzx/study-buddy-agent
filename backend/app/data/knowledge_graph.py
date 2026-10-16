"""个人学习知识图谱：构建、遍历、序列化、持久化，以及面向 Agent 的查询工具。"""
import os
import pickle

import networkx as nx
from langchain_core.tools import tool

from app.config import settings


def build_knowledge_graph() -> nx.DiGraph:
    """个人学习知识图谱：知识点之间的依赖关系。

    边含义：A -[PREREQUISITE]-> B 表示"学 B 之前需要先懂 A"。
    """
    kg = nx.DiGraph()
    triples = [
        # 编程基础 → 框架
        ("Python 基础", "PREREQUISITE", "FastAPI", "Topic", "Topic"),
        ("异步编程", "PREREQUISITE", "FastAPI", "Topic", "Topic"),
        # 机器学习 → 向量检索
        ("线性代数", "PREREQUISITE", "Embedding", "Topic", "Topic"),
        ("Embedding", "PREREQUISITE", "向量检索", "Topic", "Topic"),
        ("向量检索", "PREREQUISITE", "RAG", "Topic", "Topic"),
        # 检索
        ("向量检索", "RELATED", "混合检索", "Topic", "Topic"),
        ("混合检索", "PREREQUISITE", "Rerank", "Topic", "Topic"),
        ("Rerank", "PREREQUISITE", "RAG", "Topic", "Topic"),
        # 评估
        ("RAG", "RELATED", "RAG 评估", "Topic", "Topic"),
        ("RAG 评估", "RELATED", "Faithfulness", "Topic", "Metric"),
        ("RAG 评估", "RELATED", "AnswerRelevancy", "Topic", "Metric"),
        ("RAG 评估", "RELATED", "ContextRecall", "Topic", "Metric"),
    ]
    for subj, rel, obj, subj_type, obj_type in triples:
        kg.add_node(subj, type=subj_type)
        kg.add_node(obj, type=obj_type)
        kg.add_edge(subj, obj, relation=rel)
    return kg


def traverse_kg(graph: nx.DiGraph, start_entity: str, max_hops: int = 2,
                filter_node_type: str = None):
    visited_edges = []
    current_layer = {start_entity}
    visited_nodes = {start_entity}
    for _ in range(max_hops):
        next_layer = set()
        for node in current_layer:
            if node not in graph:
                continue
            for successor in graph.successors(node):
                if filter_node_type and graph.nodes[successor].get("type") != filter_node_type:
                    continue
                edge_rel = graph[node][successor]["relation"]
                visited_edges.append((node, edge_rel, successor))
                if successor not in visited_nodes:
                    next_layer.add(successor)
                    visited_nodes.add(successor)
        current_layer = next_layer
        if not current_layer:
            break
    return visited_edges


def serialize_subgraph(edges) -> str:
    if not edges:
        return "（知识图谱中未找到相关实体关系）"
    return "\n".join(f"- {s} --{r}--> {o}" for s, r, o in edges)


def get_or_build_kg() -> nx.DiGraph:
    if os.path.exists(settings.KG_PATH):
        with open(settings.KG_PATH, "rb") as f:
            return pickle.load(f)
    kg = build_knowledge_graph()
    with open(settings.KG_PATH, "wb") as f:
        pickle.dump(kg, f)
    return kg


@tool
def knowledge_graph_query(entity: str, max_hops: int = 2) -> str:
    """在个人学习知识图谱上做 N 跳遍历，获取知识点之间的依赖与关联。

    当用户问"学 A 之前需要先懂什么"、"某知识点和哪些相关"、"知识体系的依赖关系"时调用。
    entity 参数为起始知识点名（如 "RAG"）。
    """
    kg = get_or_build_kg()
    if entity not in kg:
        candidates = [n for n in kg.nodes if entity in n]
        if not candidates:
            return f"（知识图谱中未找到知识点：{entity}）"
        entity = candidates[0]
    edges = traverse_kg(kg, entity, max_hops=max_hops)
    return serialize_subgraph(edges)
