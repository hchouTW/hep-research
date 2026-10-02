# CS 3: RAG architecture

**Request:** "RAG architecture with query rewriting, hybrid retrieval, reranking, and citation checking." (All four components requested, so all drawn.)
**Type:** two-lane data-flow diagram (offline indexing, online query).

```mermaid
flowchart LR
    subgraph OFF["Offline indexing"]
        DOC[(Documents)] --> CHK[Chunking + metadata] --> EMBD[Embedding model] --> VS[(Vector index)]
        CHK --> KW[(Keyword index)]
    end
    subgraph ON["Online query"]
        Q([User query]) --> RW[Query rewriting]
        RW --> EMBQ[Embedding model]
        EMBQ --> VSR[Vector search]
        RW --> KWR[Keyword search]
        VSR --> MRG[Merge + metadata filter]
        KWR --> MRG
        MRG --> RR[Reranker]
        RR --> PB[Prompt construction]
        PB --> LLM[LLM]
        LLM --> CV[Citation verification]
        CV --> ANS([Answer with citations])
    end
    VS -.-> VSR
    KW -.-> KWR
```
**Checks:** the same embedding model used offline and online (state it); retrieval is read-only on indexes (dashed access); citation verification checks answer claims against retrieved passages; optional components labeled if not present.
**Caption:** Retrieval-augmented generation pipeline. Documents are chunked, embedded, and indexed offline (top). At query time the query is rewritten and used for hybrid (vector and keyword) retrieval; results are merged, filtered, reranked, and inserted into the prompt, and the generated answer is checked against the retrieved passages before it is returned.
