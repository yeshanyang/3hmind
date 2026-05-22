"""
MemoryLayer 向后兼容桥接 → MemoryOrchestrator
保持旧调用方 (reasoning_layer.py) 无需修改
"""
from mind_layer.memory_orchestrator import MemoryOrchestrator

# MemoryLayer 别名指向 MemoryOrchestrator
MemoryLayer = MemoryOrchestrator
