# Computer Science / Information Engineering Diagrams

## 1. Separate these in every architecture figure

| Distinction | Encoding |
|---|---|
| data flow vs control flow | solid vs dashed arrow |
| sync vs async | solid filled head vs open head / dashed; queue node between async parties |
| stateless vs stateful | plain box vs cylinder or "state" marker |
| local vs remote | boundary frames (process / host / cloud / network) |
| training vs inference | separate groups; dashed = training-only |
| persistent storage vs cache | cylinder vs cylinder with "cache"/TTL note |
| request-response vs event-driven | labeled edges + broker node for events |
| orchestration vs execution | orchestrator node issuing control edges to workers |

## 2. Software architecture

Layered (presentation/service/domain/data, dependencies point downward), hexagonal (domain core, ports,
adapters; dependencies point inward), client-server, microservices (service boxes + API/queue edges,
database-per-service if true), event-driven (producers -> broker -> consumers), service-oriented,
observability (metrics/logs/traces pipeline as a side channel). Draw only components that exist (read the
repo: README, Docker/compose, manifests, API specs, configs, source imports). Dependency direction
is an edge semantic: state it ("A -> B means A imports B").

## 3. Agentic AI

Components: user, orchestrator, planner, executor, specialist agents (retrieval, coding, analysis,
verification), memory (short-term context, long-term store), tool layer (search, code execution,
database, external APIs), sandbox, vector store.

```text
User -> Orchestrator -> {Planner, Research, Coding, Verification}
                            -> Tool layer {Search, Code exec (sandbox), DB, APIs}
Memory <-> Orchestrator/agents   (read/write, label which)
Verification -> Orchestrator (feedback loop, with stop condition)
```
Checks: who has authority to call tools; which loops exist and their termination (max iterations /
success test); human-in-the-loop approval points; which messages are control (delegation) vs data
(results); trust boundary around code execution; do not draw an agent the system does not have.

## 4. RAG

`Query -> [query rewriting] -> Embedding -> Vector search (+ keyword: hybrid) -> [metadata filters] -> Retrieved docs -> [rerank] -> Prompt construction -> LLM -> Answer -> [citation verification]`.
Show *offline indexing* (documents -> chunking -> embedding -> index) as a separate lane from the
*online query* path. Brackets = optional components; mark which the system actually uses.

## 5. ML pipelines

`Raw data -> preprocessing -> feature engineering -> split (train/val/test) -> training <-> hyperparameter tuning (validation) -> evaluation (test) -> deployment`.
Leakage hazards to check: fit preprocessing on train only; test set touched once; tuning uses
validation only; test does not feed back into training. Inference path separate from training path;
shared preprocessing shown as one component used by both.

## 6. Deep-learning architecture figures

- Follow the actual tensor path; annotate shapes only if verified (`B x T x d`).
- Encode: learned module (bold/double border), fixed op (plain), loss (distinct shape), training-only
  (dashed), inference-only (dotted), skip/residual (curved or labeled edge), `⊕` add, `⊗` multiply.
- Transformer: embedding + positional encoding -> N x [(masked) self-attention -> add&norm -> FFN -> add&norm]
  -> output projection; encoder-decoder adds cross-attention; state pre-/post-norm from the code.
- CNN/ResNet/U-Net: conv stages, downsampling/upsampling, skip connections (U-Net concatenates).
- RNN/LSTM/GNN/AE/VAE (encoder -> latent `μ, σ` -> sample z via reparameterization -> decoder;
  KL + reconstruction losses), GAN (generator/discriminator, two losses), diffusion (forward
  noising fixed, reverse denoiser learned, sampler loop).
- **Conceptual vs exact**: say which. Exact layer-by-layer needs the config/code; otherwise mark
  "conceptual, hyperparameters omitted."

## 7. Distributed systems

Scheduler, workers, message broker, task queue, replicas (leader/follower with replication
direction), sharding (partition key), consensus group (Raft/Paxos members - only if used), distributed
storage. Show failure/retry paths and where ordering or idempotency matters.

## 8. Networking / Databases

Networking: clients, switches, routers, gateways, firewalls, load balancers, subnets (frames),
services; direction of traffic and trust zones. Databases: ER (entities, PK/FK, cardinality), OLTP vs OLAP
separation with ETL between, data lake / warehouse / lakehouse layers, indexes, storage hierarchy.

## 9. Sequence diagrams

Lifelines for participants; messages ordered top to bottom; sync call (solid) + return (dashed);
async message (open head); `loop`, `alt/opt`, `par` frames; retry as a `loop` with a guard;
activation bars when useful. One scenario per diagram (happy path, then a failure variant if needed).
Message names should be actual API/operation names, not prose.

## 10. Validation checklist

data vs control flow; sync vs async; stateless vs stateful; local vs remote; training vs inference;
persistent vs cache; request-response vs event-driven; orchestration vs execution; components verified
against code when code exists; assumptions listed for anything inferred.

For implementing or debugging the systems themselves see `deep-learning` (PyTorch) and
`agile-development` (architecture/ADR guidance).
