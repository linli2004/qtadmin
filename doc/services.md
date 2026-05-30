# 标准化服务设计

## 整体思路

标准化服务接收一条 `SourceRecord`，抽取结构化字段，生成一条或多条 `NormalizedRecord`。

不同类型的原始记录（图片 OCR、聊天消息、CSV 行、银行流水、表单）需要不同的标准化逻辑，因此采用**策略模式 + 管道**来组织代码。

## Normalizer 接口

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class NormalizeInput:
    source_record: "SourceRecord"
    # 可选上下文，如已有标准化记录用于追加，而非从零生成

@dataclass
class NormalizeResult:
    normalized_records: list[dict]  # NormalizedRecord 待写入字段
    links: list[dict]               # RecordLink 待写入字段

class Normalizer(ABC):
    """每种 source_type 对应一个 Normalizer 实现"""

    @abstractmethod
    def can_handle(self, source_record: "SourceRecord") -> bool:
        ...

    @abstractmethod
    def normalize(self, input: NormalizeInput) -> NormalizeResult:
        ...
```

## 注册机制

```python
# services/normalization.py

_normalizers: list[Normalizer] = []

def register_normalizer(normalizer: Normalizer) -> None:
    _normalizers.append(normalizer)

def normalize(source_record: "SourceRecord") -> NormalizeResult:
    for normalizer in _normalizers:
        if normalizer.can_handle(source_record):
            return normalizer.normalize(NormalizeInput(source_record))
    raise ValueError(f"没有能处理 source_type={source_record.source_type} 的 Normalizer")
```

## 内置 Normalizer

| Normalizer | 处理的 source_type | 说明 |
|---|---|---|
| `CsvRowNormalizer` | `csv_row` | CSV 导入，各列直接映射 |
| `BankTxNormalizer` | `bank_tx` | 银行流水，解析金额方向 |
| `ChatMessageNormalizer` | `chat` | 聊天消息，抽取关键字段 |
| `ImageOcrNormalizer` | `image` | OCR 文本，抽取关键字段 |
| `FormNormalizer` | `form` | 表单提交，字段直接映射 |
| `ApiNormalizer` | `api` | API 导入，字段直接映射 |
| `ManualNormalizer` | `manual` | 人工录入，字段直接映射 |
