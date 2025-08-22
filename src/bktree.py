from __future__ import annotations
from typing import Callable, Dict, List, Optional, Tuple

class _BKTreeNode:
    def __init__(self, term: str) -> None:
        self.term = term
        self.children: Dict[int, _BKTreeNode] = {}

class BKTree:
    """Simple BK-tree implementation for approximate string matching."""

    def __init__(self, distance_func: Callable[[str, str], int]) -> None:
        self.distance_func = distance_func
        self.root: Optional[_BKTreeNode] = None

    def add(self, term: str) -> None:
        if self.root is None:
            self.root = _BKTreeNode(term)
            return
        node = self.root
        while True:
            dist = self.distance_func(term, node.term)
            child = node.children.get(dist)
            if child is not None:
                node = child
            else:
                node.children[dist] = _BKTreeNode(term)
                break

    def search(self, term: str, max_dist: int) -> List[Tuple[str, int]]:
        if self.root is None:
            return []
        results: List[Tuple[str, int]] = []
        nodes = [self.root]
        while nodes:
            node = nodes.pop()
            dist = self.distance_func(term, node.term)
            if dist <= max_dist:
                results.append((node.term, dist))
            low = dist - max_dist
            high = dist + max_dist
            for d, child in node.children.items():
                if low <= d <= high:
                    nodes.append(child)
        return results
